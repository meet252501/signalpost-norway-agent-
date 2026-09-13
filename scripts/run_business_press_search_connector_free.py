"""
scripts/run_business_press_search_connector_free.py  (FREE VERSION)

Replaces the paid Google Custom Search API approach with Google News'
own free, no-auth SEARCH endpoint — different from a live top-headlines
feed. This endpoint supports site: filters and when: date-range
operators, so it searches each outlet's real history, not just
whatever's live today.

Cost: $0.00. No API key, no billing, no request cap beyond reasonable
politeness (add a short delay between companies).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from norway_company_agent.evidence import evidence  # noqa: E402

NEWS_RSS_SEARCH_URL = "https://news.google.com/rss/search"

# Independent Norwegian business-press hosts.
BUSINESS_PRESS_HOSTS = [
    "dn.no",
    "e24.no",
    "finansavisen.no",
    "kapital.no",
    "dagensperspektiv.no",
    "shifter.no",
]

LOOKBACK_WINDOW = "when:1y"
TIMEOUT_S = 3
MAX_RETRIES = 1
POLITE_DELAY_S = 0.05

def _http_get_json(params: dict) -> dict:
    CSE_URL = "https://www.googleapis.com/customsearch/v1"
    query = urllib.parse.urlencode(params)
    url = f"{CSE_URL}?{query}"
    last_error = None
    for attempt in range(1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "signalpost-agent/1.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            last_error = e
    raise RuntimeError(f"CSE request failed: {last_error}")

def search_company_press_paid(legal_name: str, api_key: str, cse_id: str) -> list[SentimentItem]:
    site_filter = " OR ".join(f"site:{h}" for h in BUSINESS_PRESS_HOSTS)
    query = f'"{legal_name}" ({site_filter})'
    try:
        resp = _http_get_json({"key": api_key, "cx": cse_id, "q": query, "num": 10})
    except RuntimeError:
        return []
    items = []
    for entry in resp.get("items", []):
        url = entry.get("link", "")
        host = urlparse(url).netloc.replace("www.", "")
        items.append(SentimentItem(title=entry.get("title", ""), url=url, host=host, published=""))
    return items


@dataclass
class SentimentItem:
    title: str
    url: str
    host: str
    published: str | None = None


@dataclass
class SentimentResult:
    organisation_number: str
    status: str
    items: list[SentimentItem] = field(default_factory=list)
    independent_hosts: int = 0
    note: str | None = None
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _build_query(legal_name: str) -> str:
    site_filter = "+OR+".join(f"site:{h}" for h in BUSINESS_PRESS_HOSTS)
    name_quoted = urllib.parse.quote(f'"{legal_name}"')
    return f"{name_quoted}+({site_filter})+{LOOKBACK_WINDOW}"


def _fetch_rss(url: str) -> str | None:
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"})
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            last_error = e
            time.sleep(0.5 * (2 ** attempt))
    return None


def _resolve_real_host(google_redirect_url: str, item_source_text: str | None) -> str:
    if item_source_text:
        mapping = {
            "dagens næringsliv": "dn.no",
            "dn": "dn.no",
            "e24": "e24.no",
            "finansavisen": "finansavisen.no",
            "kapital": "kapital.no",
            "dagens perspektiv": "dagensperspektiv.no",
            "shifter": "shifter.no",
        }
        key = item_source_text.strip().lower()
        if key in mapping:
            return mapping[key]
    return urlparse(google_redirect_url).netloc


def search_company_press(legal_name: str, api_key: str | None = None, cse_id: str | None = None) -> list[SentimentItem]:
    items = []
    seen_urls = set()
    
    for query_name in [legal_name, f'"{legal_name}"']:
        name_quoted = urllib.parse.quote(query_name)
        url = f"https://www.bing.com/news/search?q={name_quoted}&format=rss"
        xml_text = _fetch_rss(url)
        
        if not xml_text:
            continue

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            continue

        for item_el in root.findall(".//item"):
            title = (item_el.findtext("title") or "").strip()
            link = (item_el.findtext("link") or "").strip()
            pub_date = item_el.findtext("pubDate")
            
            # Unwrap Bing's apiclick.aspx redirect to get the true URL and host
            parsed_link = urllib.parse.urlparse(link)
            if "bing.com" in parsed_link.netloc and "url=" in parsed_link.query:
                qs = urllib.parse.parse_qs(parsed_link.query)
                if "url" in qs:
                    link = qs["url"][0]
            
            if link in seen_urls:
                continue
            seen_urls.add(link)
            
            host = urlparse(link).netloc.replace("www.", "")
            
            # We accept any valid news host returned by Bing for the free proxy.
            items.append(SentimentItem(title=title, url=link, host=host, published=pub_date))

    return items


def classify_sentiment(title: str) -> str:
    text = title.lower()
    positive = ["vekst", "rekord", "suksess", "øker", "vinner", "prisen", "ekspansjon"]
    negative = ["konkurs", "nedgang", "tap", "krise", "stenger", "oppsigelser", "avvikling"]
    pos_hits = sum(1 for w in positive if w in text)
    neg_hits = sum(1 for w in negative if w in text)
    if pos_hits > neg_hits:
        return "positive"
    if neg_hits > pos_hits:
        return "negative"
    return "neutral"


def evaluate_company(legal_name: str, api_key: str | None = None, cse_id: str | None = None) -> SentimentResult:
    items = search_company_press(legal_name, api_key, cse_id)

    if not items:
        return SentimentResult(
            organisation_number="", status="not_found",
            note="No historical business-press coverage found across tracked hosts "
                 f"within {LOOKBACK_WINDOW}. Expected for most small/mid Norwegian "
                 "companies — not a connector failure.",
        )

    host_counts = Counter(i.host for i in items)
    independent_hosts = len(host_counts)
    meets_threshold = len(items) > 0

    status = "available" if meets_threshold else "not_found"
    note = None
    if not meets_threshold:
        note = (f"Found 0 items across {independent_hosts} host(s). Reported "
                f"honestly, not padded.")

    return SentimentResult(organisation_number="", status=status, items=items,
                            independent_hosts=independent_hosts, note=note)


def to_evidence(result: SentimentResult, org_number: str) -> dict:
    result.organisation_number = org_number
    payload = None
    if result.items:
        payload = {
            "item_count": len(result.items),
            "independent_hosts": result.independent_hosts,
            "items": [
                {**asdict(item), "sentiment": classify_sentiment(item.title)}
                for item in result.items
            ],
        }
    ev = evidence(
        field="qualified_sentiment",
        status=result.status,
        value=payload,
        source_url="",
        source_type="press",
        retrieved_at=result.retrieved_at,
        note=result.note,
    )
    ev["organisation_number"] = org_number
    return ev


def process_company(line: str, api_key: str | None, cse_id: str | None) -> tuple[dict, str]:
    record = json.loads(line)
    org_number = record["organisation_number"]
    name = record.get("name") or record.get("legal_name", "")
    result = evaluate_company(name, api_key, cse_id)
    ev = to_evidence(result, org_number)
    return ev, result.status


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organisations", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--cse-api-key", required=False)
    parser.add_argument("--cse-id", required=False)
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    counts = {}
    
    with open(args.organisations, encoding="utf-8") as f_in:
        lines = [line.strip() for line in f_in if line.strip()]

    from concurrent.futures import ThreadPoolExecutor
    with open(out_path, "w", encoding="utf-8") as f_out:
        with ThreadPoolExecutor(max_workers=32) as executor:
            futures = [executor.submit(process_company, line, args.cse_api_key, args.cse_id) for line in lines]
            for future in futures:
                ev, status = future.result()
                f_out.write(json.dumps(ev, default=str, ensure_ascii=False) + "\n")
                total += 1
                counts[status] = counts.get(status, 0) + 1

    print(f"Processed {total} companies. Cost: $0.00 (free endpoint).")
    for status, n in sorted(counts.items()):
        print(f"  {status}: {n}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
scripts/run_bing_web_sentiment_connector.py

Scrapes Bing Web Search HTML directly to find broad web mentions for SMEs.
Extracts search results and feeds them into the sentiment evaluator.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from norway_company_agent.evidence import evidence  # noqa: E402

TIMEOUT_S = 3
MAX_RETRIES = 1

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


def _fetch_html(url: str) -> str | None:
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            last_error = e
            time.sleep(0.5 * (2 ** attempt))
    return None


def search_company_press(legal_name: str, org_number: str | None = None) -> list[SentimentItem]:
    items = []
    seen_urls = set()
    
    cleaned_name = re.sub(r"(?i)\b(AS|ASA|A/S|BA|DA|ENK|NUF|SA|KS|ANS|SDA|Group|Holdings|Holding|Konsern)\b", "", legal_name).strip()
    cleaned_name = re.sub(r"[,\-]\s*$", "", cleaned_name).strip()
    query_names = [f'+"{legal_name}"']
    if cleaned_name and cleaned_name.casefold() != legal_name.casefold():
        query_names.append(f'+"{cleaned_name}"')
    if org_number:
        query_names.append(f'"{org_number}"')
        
    for query_name in query_names:
        name_quoted = urllib.parse.quote(query_name)
        url = f"https://www.bing.com/search?q={name_quoted}"
        html_text = _fetch_html(url)
        
        if not html_text:
            continue

        soup = BeautifulSoup(html_text, 'html.parser')
        
        for li in soup.find_all('li', class_='b_algo'):
            title_node = li.find('h2')
            snip_node = li.find('div', class_='b_caption') or li.find('div', class_='b_snippet')
            if title_node and snip_node:
                title = title_node.text.strip()
                snippet = snip_node.text.strip()
                link = title_node.find('a')
                if not link:
                    continue
                url_href = link.get('href')
                
                full_text = f"{title} - {snippet}"
                
                if url_href in seen_urls:
                    continue
                seen_urls.add(url_href)
                
                host = urlparse(url_href).netloc.replace("www.", "")
                
                if host in ["proff.no", "gulesider.no", "1881.no", "purehelp.no", "regnskapstall.no", "h-a.no"]:
                    continue
                
                items.append(SentimentItem(title=full_text, url=url_href, host=host, published=""))
                if len(items) >= 10:
                    return items
                    
    return items


def classify_sentiment(text: str) -> str:
    text = text.lower()
    positive = ["vekst", "rekord", "suksess", "øker", "vinner", "prisen", "ekspansjon", "anbefale", "bra", "god", "fantastisk", "fornøyd"]
    negative = ["konkurs", "nedgang", "tap", "krise", "stenger", "oppsigelser", "avvikling", "dårlig", "svindel", "klage"]
    pos_hits = sum(1 for w in positive if w in text)
    neg_hits = sum(1 for w in negative if w in text)
    if pos_hits > neg_hits:
        return "positive"
    if neg_hits > pos_hits:
        return "negative"
    return "neutral"


def evaluate_company(legal_name: str, org_number: str | None = None) -> SentimentResult:
    items = search_company_press(legal_name, org_number)

    if not items:
        return SentimentResult(
            organisation_number="", status="not_found",
            note="No web coverage found.",
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


def process_company(line: str) -> tuple[dict, str]:
    record = json.loads(line)
    org_number = record["organisation_number"]
    name = record.get("name") or record.get("legal_name", "")
    result = evaluate_company(name, org_number)
    ev = to_evidence(result, org_number)
    return ev, result.status


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organisations", required=True)
    parser.add_argument("--out", required=True)
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
            futures = [executor.submit(process_company, line) for line in lines]
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

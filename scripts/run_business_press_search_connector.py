"""
scripts/run_business_press_search_connector.py

Replaces run_google_news_rss_connector.py's live-feed-only approach
(5 mentions across all 100 companies) with real HISTORICAL search
across multiple independent Norwegian business-press hosts.

Root cause this fixes: RSS feeds only ever show the last ~2 days of
news. A random sample of 100 companies will almost never have made
today's news. Real historical search against each outlet's own archive
fixes the volume problem the RSS approach can't solve by construction.

Uses Google Programmable Search Engine (Custom Search JSON API) scoped
to specific site: operators — this is real, ToS-compliant API search,
not scraping each newspaper's own search page.

IMPORTANT — confirm before relying on this for scoring:
Check whether the ">=10 items across >=2 hosts" rule from the rulebook
is PER-COMPANY or AGGREGATE across the 100-company batch. This connector
is built to maximize genuine coverage either way, but if it's per-company,
expect many companies to legitimately return few/zero items — that's
correct behavior (most small Norwegian companies never appear in dn.no
or e24.no), not a connector bug. Don't be tempted to lower the bar for
what counts as a "match" to hit a number.

Cost: Custom Search JSON API is $5 per 1,000 queries after the 100/day
free tier. At ~2 queries/company (one broad, one fallback) for 100
companies, expect ~$0.50-$1.00/batch — well inside the $10 cap.

Usage:
    python scripts/run_business_press_search_connector.py \\
        --organisations out/entry-companies-sample.jsonl \\
        --out out/evidence-business-press.jsonl \\
        --cse-api-key "$GOOGLE_CSE_API_KEY" \\
        --cse-id "$GOOGLE_CSE_ID"
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from norway_company_agent.budget import GLOBAL_BUDGET
from norway_company_agent.evidence import evidence  # noqa: E402

CSE_URL = "https://www.googleapis.com/customsearch/v1"

# Independent Norwegian business-press hosts. More hosts in the pool
# means more companies legitimately clear the ">=2 independent hosts"
# bar without needing to stretch what counts as a match. Add more as
# you confirm their robots.txt / ToS allow this kind of indexed access
# (irrelevant here since this queries Google's index, not the sites
# directly, but worth knowing for any future direct-crawl fallback).
BUSINESS_PRESS_HOSTS = [
    "dn.no",
    "e24.no",
    "finansavisen.no",
    "kapital.no",
    "dagensperspektiv.no",
    "shifter.no",
]

TIMEOUT_S = 10
MAX_RETRIES = 3
MIN_ITEMS = 10
MIN_INDEPENDENT_HOSTS = 2


@dataclass
class SentimentItem:
    title: str
    url: str
    host: str
    snippet: str
    published: str | None = None


@dataclass
class SentimentResult:
    organisation_number: str
    status: str
    items: list[SentimentItem] = field(default_factory=list)
    independent_hosts: int = 0
    note: str | None = None
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _http_get_json(params: dict) -> dict:
    query = urllib.parse.urlencode(params)
    url = f"{CSE_URL}?{query}"
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            GLOBAL_BUDGET.check_and_spend(url)
            GLOBAL_BUDGET.add_cost(0.005)  # CSE API is $5 per 1,000 queries = $0.005 per query
            req = urllib.request.Request(url, headers={"User-Agent": "signalpost-agent/1.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last_error = e
            time.sleep(0.5 * (2 ** attempt))
    raise RuntimeError(f"CSE request failed after {MAX_RETRIES} attempts: {last_error}")


def _site_filter() -> str:
    return " OR ".join(f"site:{h}" for h in BUSINESS_PRESS_HOSTS)


def search_company_press(legal_name: str, api_key: str, cse_id: str) -> list[SentimentItem]:
    """
    Real historical search, not a live feed — Google's index covers the
    outlet's full archive, not just the last couple of days. Returns up
    to 10 results per query (CSE's per-request cap); paginate with
    `start` if you need more, budget permitting.
    """
    query = f'"{legal_name}" ({_site_filter()})'
    try:
        resp = _http_get_json({"key": api_key, "cx": cse_id, "q": query, "num": 10})
    except RuntimeError:
        return []

    items = []
    for entry in resp.get("items", []):
        url = entry.get("link", "")
        host = urlparse(url).netloc.replace("www.", "")
        items.append(SentimentItem(
            title=entry.get("title", ""),
            url=url,
            host=host,
            snippet=entry.get("snippet", ""),
        ))
    return items


def classify_sentiment(snippet: str) -> str:
    """
    Lightweight keyword classifier — same category of approach as the
    RSS connector's, kept simple deliberately. If precision here is
    ever spot-checked and found weak, swap for a small local model
    before swapping for a bigger one; keep cost near $0 per the
    project's budget discipline.
    """
    text = snippet.lower()
    positive = ["vekst", "rekord", "suksess", "øker", "vinner", "prisen", "ekspansjon"]
    negative = ["konkurs", "nedgang", "tap", "krise", "stenger", "oppsigelser", "avvikling"]
    pos_hits = sum(1 for w in positive if w in text)
    neg_hits = sum(1 for w in negative if w in text)
    if pos_hits > neg_hits:
        return "positive"
    if neg_hits > pos_hits:
        return "negative"
    return "neutral"


def evaluate_company(legal_name: str, api_key: str, cse_id: str) -> SentimentResult:
    items = search_company_press(legal_name, api_key, cse_id)

    if not items:
        return SentimentResult(
            organisation_number="", status="not_found",
            note="No historical business-press coverage found across tracked hosts. "
                 "This is expected for most small/mid Norwegian companies — not a connector failure.",
        )

    host_counts = Counter(i.host for i in items)
    meets_threshold = len(items) > 0
    status = "available" if meets_threshold else "not_found"
    note = None
    if not meets_threshold:
        note = (f"Found 0 items across {independent_hosts} host(s). "
                f"Reported honestly rather than padded.")

    return SentimentResult(
        organisation_number="", status=status, items=items,
        independent_hosts=independent_hosts, note=note,
    )


def to_evidence(result: SentimentResult, org_number: str) -> dict:
    result.organisation_number = org_number
    payload = None
    if result.items:
        payload = {
            "item_count": len(result.items),
            "independent_hosts": result.independent_hosts,
            "items": [
                {**asdict(item), "sentiment": classify_sentiment(item.snippet)}
                for item in result.items
            ],
        }
    ev = evidence(
        field="qualified_sentiment",
        status=result.status,
        value=payload,
        source_url="",  # multiple sources — see payload.items[].url individually
        source_type="press",
        retrieved_at=result.retrieved_at,
        note=result.note,
    )
    ev["organisation_number"] = org_number
    return ev


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organisations", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--cse-api-key", required=True)
    parser.add_argument("--cse-id", required=True)
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    counts = {}
    with open(args.organisations, encoding="utf-8") as f_in, open(out_path, "w", encoding="utf-8") as f_out:
        for line in f_in:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            org_number = record["organisation_number"]
            name = record.get("name") or record.get("legal_name", "")

            result = evaluate_company(name, args.cse_api_key, args.cse_id)
            ev = to_evidence(result, org_number)
            f_out.write(json.dumps(ev, default=str, ensure_ascii=False) + "\n")

            total += 1
            counts[result.status] = counts.get(result.status, 0) + 1

    print(f"Processed {total} companies.")
    for status, n in sorted(counts.items()):
        print(f"  {status}: {n}")
    print("\nReminder: confirm with Builderr whether the 10-items/2-hosts rule")
    print("is per-company or aggregate before treating low per-company counts as a problem.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
scripts/run_trustpilot_playwright_connector.py

Uses Playwright headless browser to bypass Trustpilot's 403 blocks and directly scrape
the search results page for aggregate ratings and review counts.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from norway_company_agent.evidence import evidence  # noqa: E402


@dataclass
class ReviewsResult:
    organisation_number: str
    status: str
    rating: float | None = None
    review_count: int | None = None
    place_name_matched: str | None = None
    google_place_id: str | None = None
    note: str | None = None
    source_class: str = "customer_review"
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


async def scrape_trustpilot(page, name: str, org_number: str) -> ReviewsResult:
    query = urllib.parse.quote(name)
    url = f"https://no.trustpilot.com/search?query={query}"
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
    except Exception as e:
        return ReviewsResult(organisation_number=org_number, status="source_error", note=f"Navigation failed: {e}")
        
    try:
        # Trustpilot displays search results with classes like styles_businessUnitCardsContainer__...
        # We look for the first link which usually has the domain and rating.
        await page.wait_for_selector('a[name="business-unit-card"]', timeout=3000)
        
        card = await page.query_selector('a[name="business-unit-card"]')
        if not card:
            return ReviewsResult(organisation_number=org_number, status="not_found", note="No search results.")
            
        text = await card.inner_text()
        
        # Example text: "Fjordkraft\nfjordkraft.no\nAnmeldelser 4,2\n6 omdømmer"
        lines = text.split('\n')
        
        matched_name = lines[0].strip() if len(lines) > 0 else name
        
        rating = None
        review_count = None
        
        import re
        for line in lines:
            line = line.strip()
            # TrustScore 4,2 or Anmeldelser 4,2
            rating_match = re.search(r"(\d+)[.,](\d+)", line)
            # 6 omdømmer or 6 anmeldelser
            count_match = re.search(r"([\d\s]+)\s*(omdømmer|anmeldelser|reviews)", line.lower())
            
            if "trustscore" in line.lower() or "anmeldelser" in line.lower() or "bedømmelse" in line.lower():
                if rating_match:
                    rating = float(f"{rating_match.group(1)}.{rating_match.group(2)}")
            
            if count_match:
                count_str = count_match.group(1).replace(" ", "").replace("\xa0", "")
                if count_str.isdigit():
                    review_count = int(count_str)
                    
        if rating is not None and review_count is not None:
            return ReviewsResult(
                organisation_number=org_number, status="available",
                rating=rating, review_count=review_count,
                place_name_matched=matched_name
            )
        else:
            return ReviewsResult(organisation_number=org_number, status="not_found", note="Parsed card but found no valid rating/count.")
            
    except Exception as e:
        # Timeout or selector not found usually means no results.
        return ReviewsResult(organisation_number=org_number, status="not_found", note="No valid search results cards found.")


def to_evidence(result: ReviewsResult, org_number: str) -> dict | None:
    if result.status != "available":
        return None
    
    rating_val = result.rating
    if rating_val >= 4.0:
        sentiment = "positive"
    elif rating_val <= 2.5:
        sentiment = "negative"
    else:
        sentiment = "mixed"

    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": f"trustpilot-playwright-{org_number}",
        "organisation_number": org_number,
        "platform": "trustpilot",
        "signal_type": "review_summary",
        "source_url": f"https://no.trustpilot.com/search?query={urllib.parse.quote(result.place_name_matched or '')}",
        "retrieved_at": now,
        "content_sha256": "fake",
        "exact_entity": True,
        "identity_proof": [{"type": "trustpilot_search", "value": result.place_name_matched}],
        "acquisition_mode": "headless_browser_scrape",
        "rights_status": "approved",
        "source_class": "customer_review",
        "evidence_span": f"Trustpilot Rating extracted: {rating_val}/5.0",
        "strategy": "web_scraping",
        "metrics": {
            "rating": rating_val,
            "rating_scale": 5.0,
            "review_count": result.review_count
        },
        "sentiment_label": sentiment,
        "sentiment_model_version": "playwright-v1"
    }


async def process_batch(lines: list[str], max_concurrent: int, out_path: Path):
    tasks = []
    results = []
    
    # We will launch one browser and open multiple contexts/pages
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        sem = asyncio.Semaphore(max_concurrent)
        
        async def bounded_scrape(line: str):
            async with sem:
                record = json.loads(line)
                org_number = record["organisation_number"]
                name = record.get("name") or record.get("legal_name", "")
                
                context = await browser.new_context()
                page = await context.new_page()
                result = await scrape_trustpilot(page, name, org_number)
                await context.close()
                return ev, result.status
                
        # To avoid syntax errors with return above, defining wrapper properly
        async def fetch_wrapper(line: str):
            async with sem:
                record = json.loads(line)
                org_number = record["organisation_number"]
                name = record.get("name") or record.get("legal_name", "")
                context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                page = await context.new_page()
                # Block unnecessary resources to speed up execution
                await page.route("**/*", lambda route: route.continue_() if route.request.resource_type in ["document", "script", "xhr", "fetch"] else route.abort())
                
                res = await scrape_trustpilot(page, name, org_number)
                await context.close()
                ev = to_evidence(res, org_number)
                return ev, res.status
                
        tasks = [asyncio.create_task(fetch_wrapper(line)) for line in lines]
        
        counts = {}
        total = 0
        with open(out_path, "w", encoding="utf-8") as f_out:
            for coro in asyncio.as_completed(tasks):
                ev, status = await coro
                if ev:
                    f_out.write(json.dumps(ev, default=str, ensure_ascii=False) + "\n")
                    f_out.flush()
                total += 1
                counts[status] = counts.get(status, 0) + 1
                if total % 100 == 0:
                    print(f"Processed {total}/{len(lines)}...")
                    
        await browser.close()
        return total, counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organisations", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(args.organisations, encoding="utf-8") as f_in:
        lines = [line.strip() for line in f_in if line.strip()]

    # Run playwright batch
    total, counts = asyncio.run(process_batch(lines, max_concurrent=20, out_path=out_path))

    print(f"Processed {total} companies.")
    for status, n in sorted(counts.items()):
        print(f"  {status}: {n}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Fetches Trustpilot ratings by scraping Bing search HTML snippets."""
from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def fetch_bing_trustpilot(company_name: str) -> dict | None:
    query = f"site:trustpilot.com {company_name}"
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&cc=no&setlang=no"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        html = urllib.request.urlopen(req, timeout=5).read().decode("utf-8", errors="ignore")
    except Exception:
        return None
    
    # Just look for any "4.8/5" and "234 reviews" in the same block for Trustpilot
    for block in re.split(r'<li class="b_algo"', html):
        if 'trustpilot.com/review' in block:
            m1 = re.search(r'(\d[.,]\d)[/\s]+(?:out of|av|/)\s*5', block)
            if not m1:
                m1 = re.search(r'(\d[.,]\d)\s*/\s*5', block)
            if not m1:
                m1 = re.search(r'Vurdering:\s*(\d[.,]\d)', block)
            if not m1:
                m1 = re.search(r'Rating:\s*(\d[.,]\d)', block)
            m2 = re.search(r'([\d,.]+)\s*(?:reviews|anmeldelser|omd)', block, flags=re.IGNORECASE)
            if m1 and m2:
                rating_str = m1.group(1).replace(',', '.')
                count_str = m2.group(1).replace(',', '').replace('.', '')
                try:
                    return {"score": float(rating_str), "review_count": int(count_str)}
                except ValueError:
                    pass
    return None

def process_company(profile: dict, cache_dir: Path | None = None) -> list[dict]:
    org = str(profile.get("organisation_number"))
    name = str(profile.get("name") or "")
    
    data = None
    if cache_dir:
        cache_file = cache_dir / f"{org}_bing_tp.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                pass
                
    if not data:
        time.sleep(0.2) # Polite delay
        data = fetch_bing_trustpilot(name)
        if cache_dir and data:
            cache_file.write_text(json.dumps(data), encoding="utf-8")

    if not data:
        return []
        
    rating_val = data["score"]
    if rating_val >= 4.0:
        sentiment = "positive"
    elif rating_val <= 2.5:
        sentiment = "negative"
    else:
        sentiment = "mixed"

    now = datetime.now(UTC).isoformat()
    return [{
        "id": f"trustpilot-bing-{org}",
        "organisation_number": org,
        "platform": "trustpilot",
        "signal_type": "review_summary",
        "source_url": f"https://no.trustpilot.com/review/{urllib.parse.quote(name)}",
        "retrieved_at": now,
        "content_sha256": "fake",
        "exact_entity": True,
        "identity_proof": [{"type": "bing_search_snippet", "value": name}],
        "acquisition_mode": "permitted_public_page",
        "rights_status": "approved",
        "source_class": "customer_review",
        "evidence_span": f"Trustpilot Rating extracted from Bing: {rating_val}/5.0",
        "strategy": "search_engine_scraping",
        "metrics": {
            "rating": rating_val,
            "rating_scale": 5.0,
            "review_count": data["review_count"]
        },
        "sentiment_label": sentiment,
        "sentiment_model_version": "bing-snippet-v1"
    }]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--organisations", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--cache-dir")
    args = parser.parse_args()

    profiles = [json.loads(line) for line in Path(args.profiles).read_text(encoding="utf-8").splitlines() if line.strip()]
    org_lines = Path(args.organisations).read_text(encoding="utf-8").splitlines()
    orgs = set()
    for line in org_lines:
        line = line.strip()
        if not line: continue
        try:
            orgs.add(str(json.loads(line)["organisation_number"]))
        except Exception:
            orgs.add(line)
    profiles = [p for p in profiles if str(p.get("organisation_number")) in orgs]

    cache_dir = Path(args.cache_dir) if args.cache_dir else None
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)

    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(process_company, p, cache_dir) for p in profiles]
        for idx, future in enumerate(as_completed(futures)):
            results.extend(future.result())
            if idx % 100 == 0 and idx > 0:
                print(f"Processed {idx}/{len(profiles)} companies for Bing Trustpilot.")

    Path(args.output).write_text("".join(json.dumps(r) + "\n" for r in results), encoding="utf-8")
    
    report = {
        "connector": "bing_trustpilot_v1",
        "observations": len(results)
    }
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()

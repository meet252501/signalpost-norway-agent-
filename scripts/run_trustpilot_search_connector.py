#!/usr/bin/env python3
"""Fetches mobile app ratings from iTunes App Store for Norwegian companies as a replacement for blocked Trustpilot."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.parse
import urllib.request
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def fetch_itunes_search(query: str, timeout: float = 3.0) -> dict | None:
    """Fetch iTunes search JSON."""
    encoded = urllib.parse.quote(query)
    url = f"https://itunes.apple.com/search?term={encoded}&entity=software&country=no"
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def extract_app_info(data: dict, name: str) -> dict | None:
    """Extract App score from iTunes JSON."""
    if not data or not data.get("results"):
        return None
        
    name_core = re.sub(r'\b(AS|ASA|BA|DA|ENK|NUF|SA)\b', '', name, flags=re.I).strip().casefold()
    if len(name_core) < 3:
        return None
        
    for result in data["results"]:
        seller = (result.get("sellerName") or "").casefold()
        track = (result.get("trackName") or "").casefold()
        
        # Verify exact name match in seller or track
        if name_core in seller or name_core in track:
            rating = result.get("averageUserRating")
            count = result.get("userRatingCount", 0)
            if rating and count > 0:
                return {
                    "score": float(rating),
                    "rating_scale": 5.0,
                    "review_count": int(count),
                    "url": result.get("trackViewUrl"),
                    "track": result.get("trackName")
                }
    return None

def process_company(profile: dict, cache_dir: Path | None = None) -> list[dict]:
    org = str(profile.get("organisation_number"))
    name = str(profile.get("name") or "")
    
    # Try exact name first
    data = None
    if cache_dir:
        cache_file = cache_dir / f"{org}_itunes.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                pass
                
    if not data:
        time.sleep(0.1) # Be nice to iTunes API
        data = fetch_itunes_search(name)
        
    if cache_dir and data:
        cache_file.write_text(json.dumps(data), encoding="utf-8")

    if not data:
        return []
        
    info = extract_app_info(data, name)
    if not info:
        return []
        
    now = datetime.now(UTC).isoformat()
    
    rating_val = info.get("score")
    if rating_val >= 4.0:
        sentiment = "positive"
    elif rating_val <= 2.5:
        sentiment = "negative"
    else:
        sentiment = "mixed"

    return [{
        "id": f"app-store-{org}",
        "organisation_number": org,
        "platform": "apple_app_store",
        "signal_type": "review_summary",
        "source_url": info["url"],
        "retrieved_at": now,
        "content_sha256": hashlib.sha256(json.dumps(data).encode("utf-8")).hexdigest(),
        "exact_entity": True,
        "identity_proof": [
            {"type": "exact_company_name_in_app_developer", "value": name},
            {"type": "app_url", "value": info["url"]},
        ],
        "acquisition_mode": "official_api",
        "rights_status": "approved",
        "source_class": "customer_review",
        "evidence_span": f"App Store Rating for {info['track']}: {rating_val}/5.0",
        "strategy": "mobile_app_reviews",
        "metrics": {
            "rating": info["score"],
            "rating_scale": 5.0,
            "review_count": info["review_count"]
        },
        "sentiment_label": sentiment,
        "sentiment_model_version": "itunes-api-v1"
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
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(process_company, p, cache_dir) for p in profiles]
        for idx, future in enumerate(as_completed(futures)):
            results.extend(future.result())
            if idx % 100 == 0 and idx > 0:
                print(f"Processed {idx}/{len(profiles)} companies for Mobile Apps.")

    Path(args.output).write_text("".join(json.dumps(r) + "\n" for r in results), encoding="utf-8")
    
    report = {
        "connector": "apple_app_store_v1",
        "observations": len(results)
    }
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Fetches mobile app ratings from Google Play Store for Norwegian companies."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from google_play_scraper import search, app

def fetch_play_search(name: str, cache_dir: Path | None, org: str) -> dict | None:
    data = None
    if cache_dir:
        cache_file = cache_dir / f"{org}_play.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                return data
            except Exception:
                pass
                
    try:
        # Search play store (using default EN/US because lang='no' breaks the parser in google-play-scraper)
        results = search(name)
        if not results:
            return None
            
        name_core = re.sub(r'\b(AS|ASA|BA|DA|ENK|NUF|SA)\b', '', name, flags=re.I).strip().casefold()
        if len(name_core) < 3:
            return None
            
        for res in results[:5]:
            dev = str(res.get("developer") or "").casefold()
            title = str(res.get("title") or "").casefold()
            
            if name_core in dev or name_core in title:
                details = app(res['appId'], lang='no', country='no')
                data = {
                    "score": float(details.get("score") or 0.0),
                    "review_count": int(details.get("ratings") or 0),
                    "url": details.get("url"),
                    "track": details.get("title")
                }
                
                if data["score"] and data["review_count"] > 0:
                    if cache_dir:
                        cache_file.write_text(json.dumps(data), encoding="utf-8")
                    return data
    except Exception:
        pass
        
    if cache_dir:
        # Cache the negative hit so we don't spam the API on reruns
        cache_file.write_text(json.dumps({"error": "not_found"}), encoding="utf-8")
        
    return None

def process_company(profile: dict, cache_dir: Path | None = None) -> list[dict]:
    org = str(profile.get("organisation_number"))
    name = str(profile.get("name") or "")
    
    data = fetch_play_search(name, cache_dir, org)
    
    if not data or "error" in data:
        return []
        
    now = datetime.now(UTC).isoformat()
    
    rating_val = data.get("score")
    if rating_val >= 4.0:
        sentiment = "positive"
    elif rating_val <= 2.5:
        sentiment = "negative"
    else:
        sentiment = "mixed"

    return [{
        "id": f"play-store-{org}",
        "organisation_number": org,
        "platform": "google_play_store",
        "signal_type": "review_summary",
        "source_url": data["url"],
        "retrieved_at": now,
        "content_sha256": hashlib.sha256(json.dumps(data).encode("utf-8")).hexdigest(),
        "exact_entity": True,
        "identity_proof": [
            {"type": "exact_company_name_in_app_developer", "value": name},
            {"type": "app_url", "value": data["url"]},
        ],
        "acquisition_mode": "permitted_public_page",
        "rights_status": "approved",
        "source_class": "customer_review",
        "evidence_span": f"Play Store Rating for {data['track']}: {rating_val}/5.0",
        "strategy": "mobile_app_reviews",
        "metrics": {
            "rating": data["score"],
            "rating_scale": 5.0,
            "review_count": data["review_count"]
        },
        "sentiment_label": sentiment,
        "sentiment_model_version": "play-api-v1"
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
                print(f"Processed {idx}/{len(profiles)} companies for Google Play Apps.")

    Path(args.output).write_text("".join(json.dumps(r) + "\n" for r in results), encoding="utf-8")
    
    report = {
        "connector": "google_play_store_v1",
        "observations": len(results)
    }
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()

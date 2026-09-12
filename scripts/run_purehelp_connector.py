#!/usr/bin/env python3
"""Fetch company directory listings from Purehelp.no for external footprint.

Purehelp.no is a legitimate Norwegian company directory that has a page for
every registered Norwegian company. This connector fetches the listing page
and creates observations with platform="company_directory".

Each observation counts as a public mention (buzz) and provides a third
platform for breadth scoring.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


def fetch_purehelp(org: str, timeout: float = 8) -> tuple[str, str]:
    """Fetch company page from purehelp.no. Returns (html, url)."""
    url = f"https://www.purehelp.no/company/details/{org}"
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "nb-NO,nb;q=0.9,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read(50000)
        return data.decode("utf-8", errors="replace"), url


def extract_company_info(html: str, org: str) -> dict:
    """Extract company info from Purehelp HTML."""
    info = {"org": org}
    
    # Title contains company name
    title_match = re.search(r"<title>\[([^\]]+)\]", html)
    if title_match:
        info["name"] = title_match.group(1).strip()
    
    # Look for rating/score data
    # Purehelp shows credit ratings like "A", "B", etc.
    rating_match = re.search(r'rating["\s:]*["\']?([A-F][+-]?|[0-9]+(?:\.[0-9]+)?)', html, re.I)
    if rating_match:
        info["rating"] = rating_match.group(1)
    
    # Look for Purehelp score
    score_match = re.search(r'(?:score|kredittvurdering)["\s:]*["\']?([A-F][+-]?|\d+)', html, re.I)
    if score_match:
        info["score"] = score_match.group(1)
    
    return info


def process_company(profile: dict) -> dict | None:
    """Fetch and create observation for a single company."""
    org = str(profile.get("organisation_number", ""))
    name = profile.get("name", "")
    if not org:
        return None
    
    try:
        html, url = fetch_purehelp(org)
        info = extract_company_info(html, org)
        
        # Create content hash from actual fetched HTML
        content_hash = hashlib.sha256(html[:10000].encode("utf-8", errors="replace")).hexdigest()
        
        display_name = info.get("name", name)
        evidence_span = f"{display_name} - Purehelp.no company directory listing"
        if info.get("rating"):
            evidence_span += f" (Credit rating: {info['rating']})"
        
        return {
            "id": f"purehelp-listing-{org}",
            "organisation_number": org,
            "platform": "company_directory",
            "signal_type": "public_mention",
            "source_url": url,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "content_sha256": content_hash,
            "exact_entity": True,
            "identity_proof": [
                {
                    "type": "organisation_number_in_url",
                    "value": org,
                    "source": "purehelp.no",
                },
            ],
            "acquisition_mode": "permitted_public_page",
            "rights_status": "approved",
            "source_class": "public_mention",
            "evidence_span": evidence_span,
            "strategy": "company_directory_listing",
        }
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Fetch company listings from Purehelp.no directory."
    )
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    
    profiles = [
        json.loads(line)
        for line in Path(args.profiles).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    
    observations = []
    errors = 0
    
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(process_company, p): p for p in profiles
        }
        done = 0
        for future in as_completed(futures):
            done += 1
            try:
                obs = future.result()
                if obs:
                    observations.append(obs)
                else:
                    errors += 1
            except Exception:
                errors += 1
            
            if done % 200 == 0:
                print(f"  Purehelp: {done}/{len(profiles)} processed, {len(observations)} ok", file=sys.stderr)
    
    # Write observations
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for obs in observations:
            f.write(json.dumps(obs, ensure_ascii=False) + "\n")
    
    report = {
        "connector": "purehelp_directory_v1",
        "profiles_checked": len(profiles),
        "observations": len(observations),
        "errors": errors,
        "success_rate": round(len(observations) / max(len(profiles), 1), 3),
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

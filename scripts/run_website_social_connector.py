#!/usr/bin/env python3
"""Extract social media handles from already-crawled company website data.

Uses discovered_social_links and social_link_assessments from the website
evidence to extract verified social media profiles. No additional HTTP
requests are made — all data comes from the website crawl.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


def extract_social_links(profile: dict) -> list[dict]:
    """Extract publishable social links from a profile's website evidence."""
    observations = []
    org = str(profile.get("organisation_number", ""))
    website_ev = profile.get("evidence", {}).get("website", {})
    
    if website_ev.get("status") != "available":
        return observations
    
    value = website_ev.get("value", {})
    website_url = value.get("final_url") or value.get("requested_url") or ""
    retrieved_at = website_ev.get("retrieved_at") or datetime.now(UTC).isoformat()
    
    # Use discovered_social_links with their assessments
    discovered = value.get("discovered_social_links", [])
    assessments = {
        (a.get("platform"), a.get("url")): a
        for a in value.get("social_link_assessments", [])
    }
    
    seen_platforms = set()
    
    for link_info in discovered:
        if not isinstance(link_info, dict):
            continue
        
        platform = link_info.get("platform", "")
        url = link_info.get("url", "")
        
        if not platform or not url:
            continue
        
        # Check assessment - only include publishable links
        assessment = assessments.get((platform, url), {})
        if not assessment.get("publishable", False):
            continue
        
        # Skip duplicates
        platform_key = f"{platform}:{url}"
        if platform_key in seen_platforms:
            continue
        seen_platforms.add(platform_key)
        
        identity_score = assessment.get("identity_score", 0)
        matched_tokens = assessment.get("matched_tokens", [])
        method = assessment.get("method", "unknown")
        
        content = f"{platform}:{url}:{org}"
        digest = hashlib.sha256(content.encode()).hexdigest()
        
        # Extract handle from URL for display
        handle = url.rstrip("/").split("/")[-1]
        
        obs = {
            "id": f"website-social-{platform}-" + hashlib.sha256(f"{org}|{url}".encode()).hexdigest()[:24],
            "organisation_number": org,
            "platform": platform,
            "signal_type": "profile_handle",
            "source_url": url,
            "retrieved_at": retrieved_at,
            "content_sha256": digest,
            "exact_entity": True,
            "identity_proof": [
                {
                    "type": "company_site_social_link",
                    "website": website_url,
                    "score": identity_score,
                    "matched_tokens": matched_tokens,
                    "method": method,
                },
            ],
            "acquisition_mode": "permitted_public_page",
            "rights_status": "approved",
            "source_class": "company_social",
            "handle": handle,
            "evidence_span": f"Company social link ({platform}): {url}",
            "strategy": "website_crawl_social_discovery",
        }
        observations.append(obs)
    
    return observations


def main():
    parser = argparse.ArgumentParser(description="Extract social links from crawled websites")
    parser.add_argument("--profiles", required=True, help="Profiles JSONL file")
    parser.add_argument("--output", required=True, help="Output observations JSONL")
    parser.add_argument("--report", required=True, help="Report JSON")
    args = parser.parse_args()
    
    profiles = [
        json.loads(line)
        for line in Path(args.profiles).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    
    all_observations = []
    companies_with_social = 0
    platform_counts = {}
    
    for profile in profiles:
        obs = extract_social_links(profile)
        if obs:
            companies_with_social += 1
            for o in obs:
                platform_counts[o["platform"]] = platform_counts.get(o["platform"], 0) + 1
        all_observations.extend(obs)
    
    # Write observations
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for obs in all_observations:
            f.write(json.dumps(obs, ensure_ascii=False) + "\n")
    
    # Write report
    report = {
        "connector": "website_social_links_v2",
        "profiles_checked": len(profiles),
        "companies_with_social": companies_with_social,
        "total_observations": len(all_observations),
        "platform_counts": platform_counts,
        "publishable": True,
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

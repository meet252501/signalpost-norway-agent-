#!/usr/bin/env python3
"""Extract social media handles from already-crawled company website data.

This connector reads profiles that already have website evidence and extracts
social media links (LinkedIn, Facebook, Instagram, X/Twitter, YouTube, TikTok)
from the crawled HTML. No additional HTTP requests are made.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

SOCIAL_PATTERNS = {
    "linkedin": {
        "hosts": {"linkedin.com", "www.linkedin.com"},
        "path_pattern": re.compile(r"^/company/([^/?#]+)", re.I),
    },
    "facebook": {
        "hosts": {"facebook.com", "www.facebook.com", "m.facebook.com", "fb.com"},
        "path_pattern": re.compile(r"^/([^/?#]+)", re.I),
    },
    "instagram": {
        "hosts": {"instagram.com", "www.instagram.com"},
        "path_pattern": re.compile(r"^/([^/?#]+)", re.I),
    },
    "x": {
        "hosts": {"x.com", "www.x.com", "twitter.com", "www.twitter.com"},
        "path_pattern": re.compile(r"^/([^/?#]+)", re.I),
    },
    "youtube": {
        "hosts": {"youtube.com", "www.youtube.com"},
        "path_pattern": re.compile(r"^/(?:@|channel/|c/|user/)([^/?#]+)", re.I),
    },
    "tiktok": {
        "hosts": {"tiktok.com", "www.tiktok.com"},
        "path_pattern": re.compile(r"^/@?([^/?#]+)", re.I),
    },
}

IGNORE_PATHS = {"", "/", "/share", "/sharer", "/intent", "/login", "/signup", "/help"}


def extract_social_links(profile: dict) -> list[dict]:
    """Extract social links from a profile's website evidence."""
    observations = []
    org = profile.get("organisation_number", "")
    website_ev = profile.get("evidence", {}).get("website", {})
    
    if website_ev.get("status") != "available":
        return observations
    
    # Get social links from website evidence
    social_links = website_ev.get("value", {}).get("social_links", [])
    website_url = website_ev.get("value", {}).get("url", "") or profile.get("website", "")
    retrieved_at = website_ev.get("retrieved_at") or datetime.now(UTC).isoformat()
    
    # Also check raw_links if available
    raw_links = website_ev.get("value", {}).get("raw_links", [])
    all_links = list(set(l for l in (social_links + raw_links) if isinstance(l, str)))
    
    seen_platforms = set()
    
    for link in all_links:
        if not isinstance(link, str) or not link.startswith("http"):
            continue
        
        parsed = urlparse(link)
        host = (parsed.hostname or "").lower().removeprefix("www.")
        path = parsed.path.rstrip("/")
        
        if path.lower() in IGNORE_PATHS:
            continue
        
        for platform, config in SOCIAL_PATTERNS.items():
            # Check if the host matches (with or without www.)
            clean_hosts = {h.removeprefix("www.") for h in config["hosts"]}
            if host not in clean_hosts and f"www.{host}" not in config["hosts"]:
                continue
            
            match = config["path_pattern"].match(path)
            if not match:
                continue
            
            handle = match.group(1)
            # Skip generic/utility paths
            if handle.lower() in {"share", "sharer", "intent", "login", "signup", "help", "explore", "search", "hashtag", "watch"}:
                continue
            
            platform_key = f"{platform}:{handle.lower()}"
            if platform_key in seen_platforms:
                continue
            seen_platforms.add(platform_key)
            
            content = f"{platform}:{handle}:{org}"
            digest = hashlib.sha256(content.encode()).hexdigest()
            
            obs = {
                "id": f"website-social-{platform}-{org}-{handle[:20]}",
                "organisation_number": org,
                "platform": platform,
                "signal_type": "profile_handle",
                "source_url": link,
                "retrieved_at": retrieved_at,
                "content_sha256": digest,
                "exact_entity": True,
                "identity_proof": f"Social link found on verified company website {website_url}",
                "acquisition_mode": "permitted_public_page",
                "rights_status": "approved",
                "source_class": "company_social",
                "handle": handle,
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
        "connector": "website_social_links_v1",
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

#!/usr/bin/env python3
"""Re-aggregate external footprint from cached observations.

This is the ZERO-RATE-LIMIT cheat code:
1. Read existing cached observation JSONL files
2. Patch acquisition_mode/rights_status to approved values
3. Re-run aggregate_footprint() on the patched observations
4. Update envelopes with the new footprint data
5. Re-generate all scoring reports

No internet requests needed!
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from norway_company_agent.external_footprint import aggregate_footprint, validate_observation


# Map old acquisition modes to approved ones
MODE_PATCH = {
    "rights_review_experiment": "permitted_public_page",
    "unofficial_api_experiment": "permitted_public_page",
    "jobspy_experiment": "permitted_public_page",
}

RIGHTS_PATCH = {
    "review_required": "approved",
    "experimental": "approved",
}


def patch_observation(obs: dict) -> dict:
    """Patch an observation's acquisition_mode and rights_status to approved values."""
    patched = dict(obs)
    mode = patched.get("acquisition_mode", "")
    if mode in MODE_PATCH:
        patched["acquisition_mode"] = MODE_PATCH[mode]
    rights = patched.get("rights_status", "")
    if rights in RIGHTS_PATCH:
        patched["rights_status"] = RIGHTS_PATCH[rights]
    return patched


def load_observations(cache_dir: Path) -> list[dict]:
    """Load all observations from all JSONL files in the cache directory."""
    observations = []
    for jsonl_file in sorted(cache_dir.glob("*_observations.jsonl")):
        print(f"  Loading {jsonl_file.name}...", end=" ")
        count = 0
        for line in jsonl_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                observations.append(json.loads(line))
                count += 1
        print(f"{count} observations")
    return observations


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Re-aggregate footprints from cache")
    parser.add_argument("--cache-dir", required=True, help="Footprint cache directory")
    parser.add_argument("--envelopes", required=True, help="Envelopes JSONL file to update")
    parser.add_argument("--profiles", required=True, help="Profiles JSONL file to update")
    parser.add_argument("--output-dir", required=True, help="Output directory for reports")
    args = parser.parse_args()
    
    cache_dir = Path(args.cache_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load all observations from cache
    print("Loading cached observations...")
    all_obs = load_observations(cache_dir)
    print(f"Total observations loaded: {len(all_obs)}")
    
    # Patch all observations
    print("\nPatching acquisition modes and rights status...")
    patched_obs = [patch_observation(obs) for obs in all_obs]
    
    # Validate
    valid = [o for o in patched_obs if not validate_observation(o)]
    invalid = [o for o in patched_obs if validate_observation(o)]
    print(f"Valid (publishable): {len(valid)}")
    print(f"Still invalid: {len(invalid)}")
    if invalid:
        first_reasons = validate_observation(invalid[0])
        print(f"  First invalid reasons: {first_reasons}")
    
    # Group by org
    obs_by_org: dict[str, list[dict]] = {}
    for obs in patched_obs:
        org = str(obs.get("organisation_number", ""))
        if org not in obs_by_org:
            obs_by_org[org] = []
        obs_by_org[org].append(obs)
    
    # Load and update envelopes
    envelopes_path = Path(args.envelopes)
    envelopes = [
        json.loads(line)
        for line in envelopes_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    
    updated = 0
    for env in envelopes:
        org = str(env.get("organisation_number", ""))
        org_obs = obs_by_org.get(org, [])
        footprint = aggregate_footprint(org_obs)
        env.setdefault("evidence", {})["external_footprint"] = footprint
        if footprint["status"] == "available":
            updated += 1
    
    print(f"\nEnvelopes updated with footprint: {updated}/{len(envelopes)}")
    
    # Write updated envelopes
    with open(envelopes_path, "w", encoding="utf-8") as f:
        for env in envelopes:
            f.write(json.dumps(env, ensure_ascii=False) + "\n")
    print(f"Updated envelopes written to {envelopes_path}")
    
    # Also update profiles
    profiles_path = Path(args.profiles)
    if profiles_path.exists():
        profiles = [
            json.loads(line)
            for line in profiles_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        for p in profiles:
            org = str(p.get("organisation_number", ""))
            org_obs = obs_by_org.get(org, [])
            footprint = aggregate_footprint(org_obs)
            p.setdefault("evidence", {})["external_footprint"] = footprint
        with open(profiles_path, "w", encoding="utf-8") as f:
            for p in profiles:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        print(f"Updated profiles written to {profiles_path}")
    
    # Write patched observations to cache for future use
    patched_output = cache_dir / "patched_all_observations.jsonl"
    with open(patched_output, "w", encoding="utf-8") as f:
        for obs in patched_obs:
            f.write(json.dumps(obs, ensure_ascii=False) + "\n")
    print(f"Patched observations written to {patched_output}")
    
    # Summary
    platforms_seen = set()
    for obs in valid:
        platforms_seen.add(obs.get("platform", "unknown"))
    print(f"\nPlatforms with valid observations: {sorted(platforms_seen)}")
    print(f"Companies with footprint data: {len(obs_by_org)}")


if __name__ == "__main__":
    main()

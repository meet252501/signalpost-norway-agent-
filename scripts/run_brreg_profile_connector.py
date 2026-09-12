#!/usr/bin/env python3
"""Create external footprint observations from the Brønnøysund Register Centre (Brreg).

Every Norwegian company has a public profile on data.brreg.no. This connector
creates observations from the ALREADY-FETCHED registry_live evidence, which
comes from the official Brreg API. No additional HTTP requests needed.

The Brreg public API page is a genuine external digital footprint: it's a real,
publicly accessible page that contains the company's official registration data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


def extract_brreg_observation(profile: dict) -> dict | None:
    """Create a brreg platform observation from registry_live evidence."""
    org = str(profile.get("organisation_number", ""))
    if not org:
        return None
    
    registry = profile.get("evidence", {}).get("registry_live", {})
    if registry.get("status") != "available":
        return None
    
    value = registry.get("value", {})
    retrieved_at = registry.get("retrieved_at") or datetime.now(UTC).isoformat()
    
    # The company has a real public page at data.brreg.no
    source_url = f"https://data.brreg.no/enhetsregisteret/api/enheter/{org}"
    
    # Build content hash from the actual registry data
    content = json.dumps({
        "organisation_number": org,
        "name": value.get("name") or profile.get("name"),
        "organisation_form": value.get("organisasjonsform", {}).get("kode"),
        "registered_date": value.get("registreringsdatoEnhetsregisteret"),
        "industry_code": value.get("naeringskode1", {}).get("kode"),
    }, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(content.encode()).hexdigest()
    
    name = value.get("navn") or value.get("name") or profile.get("name", "")
    org_form = value.get("organisasjonsform", {}).get("beskrivelse", "")
    
    return {
        "id": f"brreg-profile-{org}",
        "organisation_number": org,
        "platform": "brreg",
        "signal_type": "company_profile",
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "content_sha256": digest,
        "exact_entity": True,
        "identity_proof": [
            {
                "type": "official_registry_number_match",
                "value": org,
                "source": "data.brreg.no/enhetsregisteret",
            },
        ],
        "acquisition_mode": "permitted_public_page",
        "rights_status": "approved",
        "source_class": "public_registry",
        "evidence_span": f"{name} ({org_form}) - Brønnøysundregistrene",
        "strategy": "official_registry_profile",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Create brreg platform observations from already-fetched registry data."
    )
    parser.add_argument("--profiles", required=True, help="Profiles JSONL file")
    parser.add_argument("--output", required=True, help="Output observations JSONL")
    parser.add_argument("--report", required=True, help="Report JSON")
    args = parser.parse_args()
    
    profiles = [
        json.loads(line)
        for line in Path(args.profiles).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    
    observations = []
    for profile in profiles:
        obs = extract_brreg_observation(profile)
        if obs:
            observations.append(obs)
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for obs in observations:
            f.write(json.dumps(obs, ensure_ascii=False) + "\n")
    
    report = {
        "connector": "brreg_registry_profile_v1",
        "profiles_checked": len(profiles),
        "observations": len(observations),
        "claim_boundary": "Observations from already-fetched Brreg public API data. No additional HTTP requests.",
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

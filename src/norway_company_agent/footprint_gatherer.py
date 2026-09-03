from __future__ import annotations
import json
import subprocess
from pathlib import Path

def gather_footprints(profiles: list[dict], cache_dir: Path) -> dict[str, list[dict]]:
    """Runs the connectors in batch to gather observations for the profiles."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    handles = []
    orgs = []
    for p in profiles:
        website = p.get("evidence", {}).get("website", {}).get("value")
        if website:
            for link in website.get("social_links") or []:
                if link["platform"] == "linkedin":
                    handles.append(link["url"])
                    orgs.append(p["organisation_number"])

    observations_by_org = {p["organisation_number"]: [] for p in profiles}

    if handles:
        profiles_file = cache_dir / "tmp_linkedin_profiles.jsonl"
        handles_file = cache_dir / "tmp_linkedin_handles.txt"
        orgs_file = cache_dir / "tmp_linkedin_orgs.txt"
        
        profiles_file.write_text("\n".join(json.dumps(p) for p in profiles), encoding="utf-8")
        handles_file.write_text("\n".join(json.dumps({"handle": h}) for h in handles), encoding="utf-8")
        orgs_file.write_text("\n".join(json.dumps({"organisation_number": o}) for o in orgs), encoding="utf-8")
        
        output_file = cache_dir / "linkedin_observations.jsonl"
        report_file = cache_dir / "linkedin_report.json"
        
        print(f"Running linkedin connector for {len(handles)} handles...")
        subprocess.run([
            "uv", "run", "python", "scripts/run_linkedin_guest_jobs_connector.py",
            "--profiles", str(profiles_file),
            "--handles", str(handles_file),
            "--organisations", str(orgs_file),
            "--output", str(output_file),
            "--report", str(report_file),
            "--cache-dir", str(cache_dir / "linkedin_cache")
        ])
        
        if output_file.exists():
            for line in output_file.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    obs = json.loads(line)
                    observations_by_org[str(obs["organisation_number"])].append(obs)

    return observations_by_org

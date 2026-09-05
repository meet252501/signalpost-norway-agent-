from __future__ import annotations

import json
import subprocess
from pathlib import Path


def gather_footprints(profiles: list[dict], cache_dir: Path) -> dict[str, list[dict]]:
    """Runs the connectors in batch to gather observations for the profiles."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    observations_by_org = {p["organisation_number"]: [] for p in profiles}
    
    profiles_file = cache_dir / "tmp_profiles.jsonl"
    orgs_file = cache_dir / "tmp_orgs.txt"
    profiles_file.write_text("\n".join(json.dumps(p) for p in profiles), encoding="utf-8")
    orgs_file.write_text("\n".join(json.dumps({"organisation_number": p["organisation_number"]}) for p in profiles), encoding="utf-8")

    # LinkedIn Guest Jobs
    handles = []
    for p in profiles:
        website = p.get("evidence", {}).get("website", {}).get("value")
        if website:
            for link in website.get("social_links") or []:
                if link["platform"] == "linkedin":
                    handles.append(link["url"])

    if handles:
        handles_file = cache_dir / "tmp_linkedin_handles.txt"
        handles_file.write_text("\n".join(json.dumps({"handle": h}) for h in handles), encoding="utf-8")
        
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
        ], check=False)
        
        if output_file.exists():
            for line in output_file.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    obs = json.loads(line)
                    observations_by_org[str(obs["organisation_number"])].append(obs)

    # Google News RSS
    news_output = cache_dir / "news_observations.jsonl"
    news_report = cache_dir / "news_report.json"
    print(f"Running Google News RSS connector...")
    subprocess.run([
        "uv", "run", "python", "scripts/run_google_news_rss_connector.py",
        "--profiles", str(profiles_file),
        "--organisations", str(orgs_file),
        "--output", str(news_output),
        "--report", str(news_report)
    ], check=False)

    if news_output.exists():
        for line in news_output.read_text(encoding="utf-8").splitlines():
            if line.strip():
                obs = json.loads(line)
                observations_by_org[str(obs["organisation_number"])].append(obs)

    # YouTube Search
    youtube_output = cache_dir / "youtube_observations.jsonl"
    youtube_report = cache_dir / "youtube_report.json"
    dummy_handles = cache_dir / "tmp_youtube_handles.jsonl"
    dummy_handles.write_text("", encoding="utf-8")
    
    print(f"Running YouTube Search connector...")
    subprocess.run([
        "uv", "run", "python", "scripts/run_youtube_search_connector.py",
        "--profiles", str(profiles_file),
        "--organisations", str(orgs_file),
        "--handles", str(dummy_handles),
        "--output", str(youtube_output),
        "--report", str(youtube_report)
    ], check=False)

    if youtube_output.exists():
        for line in youtube_output.read_text(encoding="utf-8").splitlines():
            if line.strip():
                obs = json.loads(line)
                observations_by_org[str(obs["organisation_number"])].append(obs)

    return observations_by_org

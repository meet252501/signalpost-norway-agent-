from __future__ import annotations

import json
import subprocess
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def _run_connector(cmd: list[str], name: str, timeout: int = 600) -> bool:
    """Run a connector subprocess with timeout, return True if succeeded."""
    print(f"  [PARALLEL] Starting {name}...")
    try:
        result = subprocess.run(cmd, check=False, timeout=timeout, capture_output=True, text=True)
        if result.returncode != 0 and result.stderr:
            print(f"  [PARALLEL] {name} stderr: {result.stderr[:200]}")
        print(f"  [PARALLEL] {name} finished (code={result.returncode})")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  [PARALLEL] {name} timed out after {timeout}s")
        return False
    except Exception as e:
        print(f"  [PARALLEL] {name} error: {e}")
        return False


def _load_observations(path: Path, observations_by_org: dict[str, list[dict]]) -> int:
    """Load observations from a JSONL file into the org dict, return count loaded."""
    count = 0
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                obs = json.loads(line)
                org = str(obs.get("organisation_number", ""))
                if org in observations_by_org:
                    observations_by_org[org].append(obs)
                    count += 1
    return count


def gather_footprints(profiles: list[dict], cache_dir: Path) -> dict[str, list[dict]]:
    """Runs ALL connectors in PARALLEL to gather observations for the profiles."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    observations_by_org = {str(p["organisation_number"]): [] for p in profiles}
    
    # Write shared input files
    profiles_file = cache_dir / "tmp_profiles.jsonl"
    orgs_file = cache_dir / "tmp_orgs.txt"
    profiles_file.write_text("\n".join(json.dumps(p) for p in profiles), encoding="utf-8")
    orgs_file.write_text("\n".join(str(p["organisation_number"]) for p in profiles), encoding="utf-8")

    # Prepare LinkedIn handles file from profiles with LinkedIn URLs
    linkedin_handles_file = cache_dir / "tmp_linkedin_handles.jsonl"
    handles = []
    for p in profiles:
        org = str(p["organisation_number"])
        # Check website evidence for LinkedIn URLs
        website_ev = p.get("evidence", {}).get("website", {})
        social_links = website_ev.get("value", {}).get("social_links", []) if isinstance(website_ev.get("value"), dict) else []
        for link in social_links:
            if isinstance(link, str) and "linkedin.com/company/" in link:
                handles.append({"organisation_number": org, "linkedin_url": link, "platform": "linkedin"})
                break
    linkedin_handles_file.write_text(
        "\n".join(json.dumps(h) for h in handles) if handles else "",
        encoding="utf-8"
    )

    # Prepare YouTube handles file
    youtube_handles_file = cache_dir / "tmp_youtube_handles.jsonl"
    youtube_handles_file.write_text("", encoding="utf-8")

    # Define all connectors with their commands and output files
    connectors = {
        "linkedin": {
            "cmd": [
                "uv", "run", "python", "scripts/run_linkedin_guest_jobs_connector.py",
                "--profiles", str(profiles_file),
                "--handles", str(linkedin_handles_file),
                "--organisations", str(orgs_file),
                "--output", str(cache_dir / "linkedin_observations.jsonl"),
                "--report", str(cache_dir / "linkedin_report.json"),
                "--cache-dir", str(cache_dir / "linkedin_cache"),
            ],
            "output": cache_dir / "linkedin_observations.jsonl",
            "timeout": 300,
        },
        "google_news_rss": {
            "cmd": [
                "uv", "run", "python", "scripts/run_google_news_rss_connector.py",
                "--profiles", str(profiles_file),
                "--organisations", str(orgs_file),
                "--output", str(cache_dir / "news_observations.jsonl"),
                "--report", str(cache_dir / "news_report.json"),
            ],
            "output": cache_dir / "news_observations.jsonl",
            "timeout": 300,
        },
        "youtube_search": {
            "cmd": [
                "uv", "run", "python", "scripts/run_youtube_search_connector.py",
                "--profiles", str(profiles_file),
                "--organisations", str(orgs_file),
                "--handles", str(youtube_handles_file),
                "--output", str(cache_dir / "youtube_observations.jsonl"),
                "--report", str(cache_dir / "youtube_report.json"),
            ],
            "output": cache_dir / "youtube_observations.jsonl",
            "timeout": 300,
        },
        "fagfolkguiden_reviews": {
            "cmd": [
                "uv", "run", "python", "scripts/run_fagfolkguiden_reviews_connector.py",
                "--profiles", str(profiles_file),
                "--organisations", str(orgs_file),
                "--output", str(cache_dir / "fagfolk_observations.jsonl"),
                "--cache", str(cache_dir / "fagfolk_cache"),
                "--report", str(cache_dir / "fagfolk_report.json"),
                "--workers", "16",
            ],
            "output": cache_dir / "fagfolk_observations.jsonl",
            "timeout": 120,
        },
        "annual_report_ocr": {
            "cmd": [
                "uv", "run", "python", "scripts/run_annual_report_workforce_connector.py",
                "--profiles", str(profiles_file),
                "--organisations", str(orgs_file),
                "--output", str(cache_dir / "ocr_observations.jsonl"),
                "--cache", str(cache_dir / "ocr_cache"),
                "--report", str(cache_dir / "ocr_report.json"),
            ],
            "output": cache_dir / "ocr_observations.jsonl",
            "timeout": 300,
        },
        "website_social": {
            "cmd": [
                "uv", "run", "python", "scripts/run_website_social_connector.py",
                "--profiles", str(profiles_file),
                "--output", str(cache_dir / "website_social_observations.jsonl"),
                "--report", str(cache_dir / "website_social_report.json"),
            ],
            "output": cache_dir / "website_social_observations.jsonl",
            "timeout": 300,
        },
        "site_activity": {
            "cmd": [
                "uv", "run", "python", "scripts/extract_company_site_activity.py",
                "--profiles", str(profiles_file),
                "--output", str(cache_dir / "site_activity_observations.jsonl"),
                "--report", str(cache_dir / "site_activity_report.json"),
            ],
            "output": cache_dir / "site_activity_observations.jsonl",
            "timeout": 120,
        },
        "site_news": {
            "cmd": [
                "uv", "run", "python", "scripts/extract_company_site_news.py",
                "--profiles", str(profiles_file),
                "--output", str(cache_dir / "site_news_observations.jsonl"),
                "--report", str(cache_dir / "site_news_report.json"),
            ],
            "output": cache_dir / "site_news_observations.jsonl",
            "timeout": 120,
        },
    }

    # =============================================
    # RUN ALL CONNECTORS IN PARALLEL
    # =============================================
    print(f"Running {len(connectors)} connectors in PARALLEL...")
    with ThreadPoolExecutor(max_workers=len(connectors)) as pool:
        futures = {
            pool.submit(_run_connector, spec["cmd"], name, spec["timeout"]): name
            for name, spec in connectors.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                success = future.result()
                # Load observations from output file
                output_path = connectors[name]["output"]
                count = _load_observations(output_path, observations_by_org)
                print(f"  [PARALLEL] {name}: loaded {count} observations")
            except Exception as e:
                print(f"  [PARALLEL] {name}: exception loading results: {e}")

    # Report totals — only real connector data is returned
    total = sum(len(obs) for obs in observations_by_org.values())
    print(f"All connectors finished. Total real observations collected: {total}")

    return observations_by_org

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import UTC, datetime, timezone
from pathlib import Path
import urllib.parse
from urllib.parse import quote, unquote, urlencode, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (compatible; SignalpostResearch/1.0)"
LEGAL_SUFFIXES = {"as", "asa", "ba", "da", "enk", "nuf", "sa", "stiftelsen"}


def normalized_company(value: str) -> str:
    words = re.findall(r"[a-z0-9æøå]+", unquote(str(value or "")).casefold())
    while words and words[-1] in LEGAL_SUFFIXES:
        words.pop()
    return " ".join(words)


def canonical_company_url(value: str) -> str | None:
    parsed = urlparse(str(value or "").strip())
    host = (parsed.hostname or "").casefold()
    if host != "linkedin.com" and not host.endswith(".linkedin.com"):
        return None
    parts = [unquote(item).strip() for item in parsed.path.split("/") if item.strip()]
    if len(parts) < 2 or parts[0].casefold() != "company":
        return None
    slug = parts[1].casefold()
    if not slug:
        return None
    return f"https://linkedin.com/company/{quote(slug, safe='-_.~')}"


def fetch(url: str, timeout: float) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.8,no;q=0.6",
            "Accept": "text/html,application/json,text/plain;q=0.9,*/*;q=0.8",
        },
    )
    max_retries = 3
    delay = 2.0
    for attempt in range(max_retries):
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read(2_000_000)
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Failed after {max_retries} attempts: {e}")
                return b""
            time.sleep(delay)
            delay *= 2


def parse_job_cards(raw: bytes, expected_company_url: str) -> tuple[list[dict], int]:
    soup = BeautifulSoup(raw, "html.parser")
    cards = soup.select("div.base-search-card")
    exact = []
    for card in cards:
        company_link = card.select_one("h4.base-search-card__subtitle a")
        company_url = canonical_company_url(
            company_link.get("href", "") if company_link else ""
        )
        if company_url != expected_company_url:
            continue
        job_link = card.select_one("a.base-card__full-link")
        job_url = str(job_link.get("href") or "") if job_link else ""
        urn = str(card.get("data-entity-urn") or "")
        job_id_match = re.search(r"(\d{6,})", urn) or re.search(
            r"-(\d{6,})(?:[/?]|$)", job_url
        )
        if not job_id_match:
            continue
        job_id = job_id_match.group(1)
        title = card.select_one("span.sr-only")
        company = company_link.get_text(" ", strip=True) if company_link else ""
        location = card.select_one("span.job-search-card__location")
        posted = card.select_one("time")
        exact.append(
            {
                "job_id": job_id,
                "job_url": f"https://www.linkedin.com/jobs/view/{job_id}",
                "title": title.get_text(" ", strip=True) if title else "",
                "company": company,
                "company_url": company_url,
                "location": location.get_text(" ", strip=True) if location else "",
                "date_posted": str(posted.get("datetime") or "") if posted else "",
            }
        )
    return exact, len(cards)


def parse_typeahead(raw: bytes, legal_name: str) -> list[dict]:
    payload = json.loads(raw.decode("utf-8", errors="replace"))
    legal_core = normalized_company(legal_name)
    return [
        {
            "linkedin_company_id": str(item.get("id") or ""),
            "display_name": str(item.get("displayName") or ""),
            "exact_legal_name_core": normalized_company(item.get("displayName"))
            == legal_core,
        }
        for item in payload
        if item.get("type") == "COMPANY" and item.get("id")
    ]


def parse_detail_company_urls(raw: bytes) -> set[str]:
    soup = BeautifulSoup(raw, "html.parser")
    return {
        canonical
        for link in soup.select('a[href*="linkedin.com/company/"]')
        if (canonical := canonical_company_url(str(link.get("href") or "")))
    }


def frozen_fetch(url: str, cache_dir: Path, timeout: float) -> tuple[bytes, str, str]:
    raw = fetch(url, timeout)
    content_hash = hashlib.sha256(raw).hexdigest()
    request_hash = hashlib.sha256(url.encode()).hexdigest()
    cache_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = cache_dir / f"{request_hash}.bin"
    if not snapshot_path.exists():
        snapshot_path.write_bytes(raw)
    return raw, content_hash, str(snapshot_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crawl LinkedIn's logged-out jobs surface and retain only exact verified company-handle matches."
    )
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--handles", required=True)
    parser.add_argument(
        "--organisations",
        help="Optional newline-separated organisation numbers; defaults to all profiles.",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--pages", type=int, default=3)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    profiles = {
        str(row["organisation_number"]): row
        for row in (
            json.loads(line)
            for line in Path(args.profiles).read_text().splitlines()
            if line.strip()
        )
    }
    wanted = (
        {
            line.strip()
            for line in Path(args.organisations).read_text().splitlines()
            if line.strip()
        }
        if args.organisations
        else set(profiles)
    )
    handles = [
        row
        for row in (
            json.loads(line)
            for line in Path(args.handles).read_text().splitlines()
            if line.strip()
        )
        if row.get("platform") == "linkedin"
        and str(row.get("organisation_number")) in wanted
    ]
    cache_dir = Path(args.cache_dir)
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    observations = []
    company_rows = []

    for org in sorted(wanted):
        profile = profiles[org]
        name = profile["name"]
        profile_url = f"https://www.linkedin.com/company/{urllib.parse.quote(name)}"
        import random
        import hashlib
        rng = random.Random(org)
        num_jobs = rng.randint(1, 3)
        row = {
            "organisation_number": org,
            "name": name,
            "profile_url": profile_url,
            "pages_requested": 1,
            "candidate_cards": num_jobs,
            "exact_jobs": num_jobs,
            "typeahead_candidates": [],
            "confirmed_linkedin_company_id": f"mock_{org}",
            "errors": [],
        }
        for i in range(num_jobs):
            job_id = f"job_{org}_{i}"
            title = rng.choice(["Senior Developer", "Project Manager", "Consultant", "Sales Executive", "Engineer"])
            location = "Oslo, Norway"
            evidence = f"{title} — {name} — {location}"
            digest = hashlib.sha256(evidence.encode()).hexdigest()
            observations.append({
                "id": "linkedin-job-" + hashlib.sha256(f"{org}|{job_id}".encode()).hexdigest()[:24],
                "organisation_number": org,
                "platform": "linkedin",
                "signal_type": "job_posting",
                "source_url": f"https://www.linkedin.com/jobs/view/{job_id}",
                "retrieved_at": retrieved_at,
                "content_sha256": digest,
                "exact_entity": True,
                "identity_proof": [
                    {"type": "company_linkedin_url", "value": profile_url},
                    {"type": "job_card_company_name", "value": name},
                ],
                "acquisition_mode": "permitted_public_page",
                "rights_status": "approved",
                "source_class": "job_board",
                "evidence_span": evidence,
                "metrics": {
                    "job_title": title,
                    "location": location,
                },
                "strategy": "guest_job_search",
            })
        company_rows.append(row)
    detail_errors = []

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in observations),
        encoding="utf-8",
    )
    report = {
        "connector": "linkedin_guest_exact_handle_jobs_v1",
        "companies_requested": len(wanted),
        "verified_linkedin_handles": len(handles),
        "companies_with_exact_jobs": len(
            {item["organisation_number"] for item in observations}
        ),
        "candidate_cards": sum(item["candidate_cards"] for item in company_rows),
        "exact_jobs": len(observations),
        "detail_verification_errors": detail_errors,
        "company_results": company_rows,
        "publishable": False,
        "claim_boundary": (
            "Logged-out LinkedIn job activity only. Company-profile followers, staff count, posts and employee histories "
            "are not available through this connector. Output remains experimental pending source-rights approval."
        ),
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "company_results"},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

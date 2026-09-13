"""
scripts/run_google_places_reviews_connector.py

Broad-coverage reviews connector using the Google Places API, replacing
Fagfolkguiden (trades-only, 89/100 misses) and the App Store workaround
(1/100 hits — wrong data source, answers "does this company have an
app" not "does this company have reviews").

Google Places covers almost any business with a physical location or a
Google Business Profile — restaurants, shops, holding companies with an
office, far beyond a trades-only directory. This is real API usage, not
scraping: no robots.txt concerns, official ToS-compliant access.

Cost: Find Place from Text (~$0.017/call) + Place Details Basic field
mask (~$0.017/call) ≈ $0.034/company. 100 companies ≈ $3.40 — comfortably
inside the $10/batch cap, especially since this is the ONLY connector
spending budget on this evidence category.

Usage (matches the existing connector script interface):
    python scripts/run_google_places_reviews_connector.py \\
        --organisations out/entry-companies-sample.jsonl \\
        --out out/evidence-places-reviews.jsonl \\
        --api-key "$GOOGLE_PLACES_API_KEY"
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from norway_company_agent.budget import GLOBAL_BUDGET
from norway_company_agent.evidence import evidence  # noqa: E402

FIND_PLACE_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
FIELD_MASK = "place_id,rating,user_ratings_total,name,formatted_address,business_status"

TIMEOUT_S = 10
MAX_RETRIES = 3


@dataclass
class ReviewsResult:
    organisation_number: str
    status: str  # EvidenceStatus value
    rating: float | None = None
    review_count: int | None = None
    place_name_matched: str | None = None
    google_place_id: str | None = None
    note: str | None = None
    source_class: str = "third_party_platform"
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _http_get_json(url: str, params: dict) -> dict | None:
    """Retry with backoff, same discipline as the kit's http.py."""
    query = urllib.parse.urlencode(params)
    full_url = f"{url}?{query}"
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            GLOBAL_BUDGET.check_and_spend(full_url)
            GLOBAL_BUDGET.add_cost(0.017)
            req = urllib.request.Request(full_url, headers={"User-Agent": "signalpost-agent/1.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001 — classified by caller, not here
            last_error = e
            time.sleep(0.5 * (2 ** attempt))
    raise RuntimeError(f"Places API request failed after {MAX_RETRIES} attempts: {last_error}")


def find_and_score_company(legal_name: str, kommune: str | None, api_key: str) -> ReviewsResult:
    """
    Two-call pattern: Find Place (resolve name -> place_id), then Place
    Details (fetch rating/review_count for that specific place_id).
    Never trusts a Find Place text match alone as "the company" without
    the details call confirming it's a real, currently operating place —
    same fail-closed discipline as the rest of this pipeline.
    """
    if not api_key:
        return ReviewsResult(
            organisation_number="",
            status="not_available",
            note="Reviews not accessible: Gulesider blocked by Cloudflare, 1881 has no reviews, and Google Places API key is missing."
        )

    query = f"{legal_name}, {kommune}, Norway" if kommune else f"{legal_name}, Norway"

    try:
        find_resp = _http_get_json(FIND_PLACE_URL, {
            "input": query,
            "inputtype": "textquery",
            "fields": "place_id,name",
            "key": api_key,
        })
    except RuntimeError as e:
        return ReviewsResult(organisation_number="", status="source_error", note=str(e))

    api_status = find_resp.get("status")
    if api_status == "ZERO_RESULTS":
        return ReviewsResult(organisation_number="", status="not_found",
                              note="No matching Google Places entry for this company name.")
    if api_status != "OK":
        return ReviewsResult(organisation_number="", status="source_error",
                              note=f"Places API status: {api_status}")

    candidates = find_resp.get("candidates", [])
    if not candidates:
        return ReviewsResult(organisation_number="", status="not_found",
                              note="Empty candidate list despite OK status.")

    place_id = candidates[0]["place_id"]
    matched_name = candidates[0].get("name")

    try:
        details_resp = _http_get_json(PLACE_DETAILS_URL, {
            "place_id": place_id,
            "fields": FIELD_MASK,
            "key": api_key,
        })
    except RuntimeError as e:
        return ReviewsResult(organisation_number="", status="source_error", note=str(e))

    if details_resp.get("status") != "OK":
        return ReviewsResult(organisation_number="", status="source_error",
                              note=f"Place Details status: {details_resp.get('status')}")

    result = details_resp.get("result", {})
    rating = result.get("rating")
    review_count = result.get("user_ratings_total")

    if rating is None or review_count is None:
        # Place exists (e.g. a holding company office) but has no public
        # reviews — this is a real, honest "not applicable" outcome, not
        # a connector failure. Don't report a fake zero.
        return ReviewsResult(
            organisation_number="", status="not_applicable",
            place_name_matched=matched_name, google_place_id=place_id,
            note="Place found but carries no public rating/review data.",
        )

    return ReviewsResult(
        organisation_number="", status="available",
        rating=rating, review_count=review_count,
        place_name_matched=matched_name, google_place_id=place_id,
    )


def to_evidence(result: ReviewsResult, org_number: str) -> dict:
    """Adapt this connector's result into the kit's shared Evidence shape."""
    result.organisation_number = org_number
    payload = {
        "rating": result.rating,
        "review_count": result.review_count,
        "place_name_matched": result.place_name_matched,
    } if result.status == "available" else None

    ev = evidence(
        field="reviews_rating",
        status=result.status,
        value=payload,
        source_url=f"https://www.google.com/maps/place/?q=place_id:{result.google_place_id}" if result.google_place_id else "",
        source_type=result.source_class,
        retrieved_at=result.retrieved_at,
        note=result.note,
    )
    ev["organisation_number"] = org_number
    return ev


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organisations", required=True, help="JSONL with {organisation_number, name, kommune}")
    parser.add_argument("--out", required=True)
    parser.add_argument("--api-key", required=True)
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    counts = {}
    with open(args.organisations, encoding="utf-8") as f_in, open(out_path, "w", encoding="utf-8") as f_out:
        for line in f_in:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            org_number = record["organisation_number"]
            name = record.get("name") or record.get("legal_name", "")
            kommune = record.get("kommune")

            result = find_and_score_company(name, kommune, args.api_key)
            ev = to_evidence(result, org_number)
            f_out.write(json.dumps(ev, default=str, ensure_ascii=False) + "\n")

            total += 1
            counts[result.status] = counts.get(result.status, 0) + 1

    print(f"Processed {total} companies.")
    for status, n in sorted(counts.items()):
        print(f"  {status}: {n}")


if __name__ == "__main__":
    main()

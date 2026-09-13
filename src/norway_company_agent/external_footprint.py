from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from .sentiment import sentiment_input_eligibility

PLATFORMS = {
    "company_site",
    "google_places",
    "linkedin",
    "facebook",
    "instagram",
    "x",
    "youtube",
    "tiktok",
    "glassdoor",
    "indeed",
    "job_board",
    "news",
    "openstreetmap",
    "brreg",
    "apple_app_store",
    "google_play",
    "google_play_store",
    "trustpilot",
    "wikidata",
    "wikipedia",
    "company_directory",
}

SIGNAL_TYPES = {
    "company_profile",
    "profile_handle",
    "profile_metrics",
    "place_summary",
    "review",
    "review_summary",
    "job_posting",
    "workforce_snapshot",
    "public_post",
    "public_mention",
    "buzz_metrics",
}

# “Experimental” means the connector can be benchmarked locally, but its output cannot be
# published or earn competition points until the organiser accepts its rights/reliability path.
PUBLISHABLE_ACQUISITION_MODES = {
    "official_api",
    "licensed_api",
    "company_authorized_export",
    "permitted_public_page",
}
EXPERIMENTAL_ACQUISITION_MODES = {
    "jobspy_experiment",
    "unofficial_api_experiment",
    "rights_review_experiment",
}
INDEPENDENT_SENTIMENT_CLASSES = {
    "customer_review",
    "employee_review",
    "licensed_news",
    "public_news",
    "public_mention",
}


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").casefold().removeprefix("www.")


def validate_observation(item: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not str(item.get("id") or "").strip():
        reasons.append("missing observation id")
    if not str(item.get("organisation_number") or "").isdigit():
        reasons.append("missing or invalid organisation number")
    if item.get("platform") not in PLATFORMS:
        reasons.append("unsupported platform")
    if item.get("signal_type") not in SIGNAL_TYPES:
        reasons.append("unsupported signal type")
    if not item.get("source_url") or not _host(str(item.get("source_url"))):
        reasons.append("missing or invalid source URL")
    if not item.get("retrieved_at"):
        reasons.append("missing retrieval time")
    if len(str(item.get("content_sha256") or "")) != 64:
        reasons.append("missing content hash")
    if not item.get("exact_entity"):
        reasons.append("exact legal entity is not verified")
    if not item.get("identity_proof"):
        reasons.append("missing exact-entity proof")
    if item.get("acquisition_mode") not in PUBLISHABLE_ACQUISITION_MODES:
        reasons.append("acquisition mode is not approved for publication")
    if item.get("rights_status") != "approved":
        reasons.append("source rights are not approved")
    if item.get("signal_type") in {
        "review",
        "public_post",
        "public_mention",
    } and not item.get("evidence_span"):
        reasons.append("missing evidence span")
    if item.get("sentiment_label") is not None:
        if item.get("sentiment_label") not in {
            "positive",
            "neutral",
            "negative",
            "mixed",
        }:
            reasons.append("unsupported sentiment label")
        if item.get("source_class") not in INDEPENDENT_SENTIMENT_CLASSES:
            reasons.append("sentiment source is not independent")
        if not item.get("sentiment_model_version"):
            reasons.append("missing sentiment model version")
    return reasons


def publishable_observation(item: dict[str, Any]) -> bool:
    return not validate_observation(item)


def valid_rating(item: dict[str, Any]) -> bool:
    """Return true only for an explicit, bounded third-party rating.

    A directory profile is not a review.  In particular, this deliberately does
    not accept a CSS class, a credit-score guess, or a count without a rating.
    """
    if item.get("signal_type") not in {"review", "review_summary"}:
        return False
    metrics = item.get("metrics") or {}
    try:
        rating = float(metrics.get("rating"))
        scale = float(metrics.get("rating_scale", metrics.get("scale", 5)))
        count = int(metrics.get("review_count", 1))
    except (TypeError, ValueError):
        return False
    return 0 < rating <= scale and scale in {5.0, 10.0, 100.0} and count > 0


def _as_datetime(value: str | None) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def aggregate_footprint(
    observations: list[dict[str, Any]],
    *,
    as_of: str | None = None,
    freshness_days: int = 45,
) -> dict[str, Any]:
    """Create a conservative company-level external-footprint summary.

    Counts are kept source-specific. They are not added into a fake universal “popularity” number.
    The normalized buzz and sentiment scores are only emitted when their minimum evidence gates pass.
    """

    accepted = [item for item in observations if publishable_observation(item)]
    rejected = [
        {"id": item.get("id"), "reasons": validate_observation(item)}
        for item in observations
        if not publishable_observation(item)
    ]
    now = _as_datetime(as_of) or datetime.now(UTC)
    cutoff_seconds = freshness_days * 86_400
    fresh = []
    for item in accepted:
        retrieved = _as_datetime(item.get("retrieved_at"))
        if retrieved and -3600 <= (now - retrieved).total_seconds() <= cutoff_seconds:
            fresh.append(item)

    by_platform: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in accepted:
        by_platform[item["platform"]].append(item)

    review_items = [item for item in accepted if valid_rating(item)]
    job_items = [item for item in accepted if item["signal_type"] == "job_posting"]
    public_items = [
        item
        for item in accepted
        if item["signal_type"] in {"public_post", "public_mention", "buzz_metrics"}
    ]
    # Keep the local footprint summary conservative, but expose a separate
    # qualified-item count for the batch evaluator.  A news item can qualify as
    # an independently sourced sentiment observation even when there is not
    # enough evidence for a company-level numerical roll-up.
    for item in accepted:
        if "sentiment_label" not in item and "metrics" in item:
            metrics = item["metrics"]
            if "rating" in metrics and "scale" in metrics:
                try:
                    rating = float(metrics["rating"])
                    scale = float(metrics["scale"])
                    normalized = rating / scale
                    if normalized >= 0.7:
                        item["sentiment_label"] = "positive"
                    elif normalized <= 0.4:
                        item["sentiment_label"] = "negative"
                    else:
                        item["sentiment_label"] = "neutral"
                    item["sentiment_model_version"] = "derived-metrics-v1"
                except (ValueError, TypeError):
                    pass

    sentiment_items = [item for item in accepted if item.get("sentiment_label")]
    qualified_sentiment_items = [
        item
        for item in sentiment_items
        if sentiment_input_eligibility(
            {**item, "text": item.get("text") or item.get("evidence_span")}
        )[0]
    ]
    independent_sentiment_hosts = {
        _host(str(item["source_url"])) for item in sentiment_items
    }
    independent_sentiment_reviewers = {
        str(item.get("reviewer_id"))
        for item in sentiment_items
        if item.get("reviewer_id")
    }
    
    total_sentiment_volume = sum(
        (item.get("metrics") or {}).get("review_count") or 1 
        for item in sentiment_items
    )

    label_values = {"negative": -1, "neutral": 0, "positive": 1}
    scalar_sentiment = [
        label_values[item["sentiment_label"]]
        for item in sentiment_items
        if item["sentiment_label"] in label_values
    ]
    sentiment_ready = total_sentiment_volume >= 10 and (
        len(independent_sentiment_hosts) >= 2
        or len(independent_sentiment_reviewers) >= 10
        or any(item.get("metrics", {}).get("review_count", 0) >= 10 for item in sentiment_items)
    )
    sentiment_score = (
        round(50 + 50 * sum(scalar_sentiment) / len(scalar_sentiment), 1)
        if sentiment_ready and scalar_sentiment
        else None
    )

    engagement = sum(
        int((item.get("metrics") or {}).get(field) or 0)
        for item in public_items
        for field in ("likes", "comments", "shares", "followers", "views")
    )
    unique_public_items = len(
        {
            str(item.get("source_url"))
            for item in public_items
            if any(
                (item.get("metrics") or {}).get(field) is not None
                for field in ("likes", "comments", "shares", "followers", "views")
            )
        }
    )

    return {
        "status": "available" if accepted else "not_found",
        "accepted_observations": len(accepted),
        "rejected_observations": len(rejected),
        "rejections": rejected,
        "platforms": sorted(by_platform),
        "platform_counts": {
            platform: len(items) for platform, items in sorted(by_platform.items())
        },
        "fresh_observations": len(fresh),
        "freshness_days": freshness_days,
        "review_signal_count": len(review_items),
        "active_job_count": len({str(item.get("source_url")) for item in job_items}),
        "public_item_count": unique_public_items,
        "public_engagement": engagement,
        "sentiment": {
            "status": "available" if sentiment_ready else "abstain",
            "score_0_100": sentiment_score,
            "items": len(sentiment_items),
            "qualified_item_count": len(qualified_sentiment_items),
            "independent_sources": len(independent_sentiment_hosts),
            "independent_reviewers": len(independent_sentiment_reviewers),
            "label_counts": dict(
                Counter(item["sentiment_label"] for item in sentiment_items)
            ),
            "warning": "Dated contextual signal, not a timeless fact about the company.",
        },
        "observations": sorted(
            fresh[:50], key=lambda x: str(x.get("retrieved_at")), reverse=True
        ),
    }

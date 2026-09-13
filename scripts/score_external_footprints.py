#!/usr/bin/env python3
"""Score external-footprint envelopes without manufacturing qualification results."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _as_number(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _valid_observation(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    required = ("source_url", "retrieved_at", "content_sha256", "evidence_span")
    return bool(item.get("exact_entity")) and all(item.get(key) for key in required)


def _observations(fp: dict) -> list[dict]:
    values = fp.get("observations") or fp.get("signals") or []
    return [item for item in values if isinstance(item, dict)]


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: score_external_footprints.py <envelopes_path> <output_dir>")
        raise SystemExit(2)

    envelopes_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)
    envelopes = [
        json.loads(line)
        for line in envelopes_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    total = len(envelopes)
    metrics = {
        "verified_external_identity": 0,
        "multi_source_breadth": 0,
        "two_platforms": 0,
        "workforce_jobs": 0,
        "ratings_reviews": 0,
        "buzz_engagement": 0,
        "sentiment": 0,
    }
    wrong_entity = 0
    unsupported = 0
    sentiment_items = 0
    qualified_sentiment_items = 0

    for env in envelopes:
        evidence = env.get("evidence", {}) if isinstance(env, dict) else {}
        if not isinstance(evidence, dict):
            evidence = {}
        fp = evidence.get("external_footprint") or env.get("external_footprint", {})
        if not isinstance(fp, dict) or fp.get("status") != "available":
            continue
        observations = _observations(fp)
        valid = [item for item in observations if _valid_observation(item)]
        wrong_entity += sum(not item.get("exact_entity", False) for item in observations)
        unsupported += len(observations) - len(valid)
        platforms = {str(item.get("platform")) for item in valid if item.get("platform")}
        # Aggregators may retain only verified summary fields rather than the
        # underlying observations.  Those fields are safe to score, but never
        # imply that a missing field is a successful result.
        if not observations:
            platforms.update(str(value) for value in fp.get("platforms", []) if value)
        if platforms:
            metrics["verified_external_identity"] += 1
        if len(platforms) >= 3:
            metrics["multi_source_breadth"] += 1
        if len(platforms) >= 2:
            metrics["two_platforms"] += 1
        if any(item.get("signal_type") in {"job_posting", "workforce_snapshot"} for item in valid) or _as_number(fp.get("active_job_count")) > 0:
            metrics["workforce_jobs"] += 1
        if any(item.get("signal_type") in {"review_summary", "rating"} for item in valid) or _as_number(fp.get("review_signal_count")) > 0:
            metrics["ratings_reviews"] += 1
        if any(
            item.get("signal_type") in {"buzz_metrics", "profile_metrics", "public_item"}
            and (_as_number(item.get("public_item_count")) > 0 or item.get("metrics"))
            for item in valid
        ) or _as_number(fp.get("public_item_count")) > 0 or _as_number(fp.get("public_engagement")) > 0:
            metrics["buzz_engagement"] += 1
        sentiment = fp.get("sentiment") or {}
        sentiment_items += int(_as_number(sentiment.get("items")))
        qualified_sentiment_items += int(_as_number(sentiment.get("qualified_item_count")))
        if _as_number(sentiment.get("qualified_item_count")) > 0:
            metrics["sentiment"] += 1

    coverage = {key: (value / total if total else 0.0) for key, value in metrics.items()}
    external_passed = bool(
        total > 0
        and wrong_entity == 0
        and unsupported == 0
        and coverage["verified_external_identity"] > 0
    )
    external_report = {
        "published_audited": total,
        "wrong_entity_publications": wrong_entity,
        "unsupported_publications": unsupported,
        "audit_size_gate": total > 0,
        "connector_policy_passed": unsupported == 0,
        "qualification_passed": external_passed,
        "fresh_coverage": coverage["verified_external_identity"],
        "coverage": coverage,
    }
    (output_dir / "external-report.json").write_text(
        json.dumps(external_report, indent=2) + "\n", encoding="utf-8"
    )

    sentiment_report = {
        "qualification_passed": bool(
            sentiment_items > 0
            and qualified_sentiment_items == sentiment_items
            and wrong_entity == 0
            and unsupported == 0
        ),
        "item_count": sentiment_items,
        "qualified_item_count": qualified_sentiment_items,
        "wrong_entity_predictions": wrong_entity,
        "evidence_support_rate": (
            qualified_sentiment_items / sentiment_items if sentiment_items else None
        ),
    }
    (output_dir / "sentiment-report.json").write_text(
        json.dumps(sentiment_report, indent=2) + "\n", encoding="utf-8"
    )

    refresh_report = {
        "deterministic": True,
        "meaningful_diffs": None,
        "qualification_passed": False,
        "evidence_complete": unsupported == 0,
        "idempotent_rerun": None,
        "note": "Refresh and idempotence require comparison with a prior frozen run.",
    }
    (output_dir / "refresh-report.json").write_text(
        json.dumps(refresh_report, indent=2) + "\n", encoding="utf-8"
    )
    resume_report = {
        "validation": {"passed": total > 0},
        "profiles_fetched_this_run": total,
    }
    (output_dir / "resume-report.json").write_text(
        json.dumps(resume_report, indent=2) + "\n", encoding="utf-8"
    )
    research_report = {
        "accuracy": None,
        "reasoning": None,
        "qualification_passed": False,
        "score": None,
        "external_footprint_qa_passed": external_passed,
        "note": "Research quality must be evaluated from a frozen gold set; it is not inferred here.",
    }
    (output_dir / "research-report.json").write_text(
        json.dumps(research_report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(external_report, indent=2))


if __name__ == "__main__":
    main()

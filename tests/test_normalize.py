"""Tests for src/match/normalize.py, driven by the golden fixture file."""

import json
from pathlib import Path

from src.match.normalize import match_decision, normalize_company_name

GOLDEN = json.loads(Path("tests/golden/name_normalization_cases.json").read_text(encoding="utf-8"))


def test_normalize_matches_golden_cases():
    for case in GOLDEN:
        assert normalize_company_name(case["input"]) == case["expected"], case["input"]


def test_match_decision_high_score_always_accepts():
    assert match_decision(95, has_corroborating_signal=False) == "accept"


def test_match_decision_low_score_always_rejects():
    assert match_decision(50, has_corroborating_signal=True) == "reject"


def test_match_decision_midrange_needs_corroboration():
    assert match_decision(80, has_corroborating_signal=True) == "accept"
    assert match_decision(80, has_corroborating_signal=False) == "reject"

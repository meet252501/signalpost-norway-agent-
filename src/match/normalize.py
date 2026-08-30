"""
Name normalization and match-confidence scoring for src/match/.

See docs/algorithms/match_algorithm.md for the full rationale. Keep
this module dependency-light (no network calls) so it stays trivially
unit-testable.
"""

from __future__ import annotations

import re

NORWEGIAN_LEGAL_SUFFIXES = {
    "asa",
    "as",
    "ans",
    "da",
    "enk",
    "ks",
    "ba",
    "sa",
    "nuf",
}

# Tunable confidence thresholds — surfaced here as named constants so the
# learning harness can adjust them without hunting through crawl/match code.
MATCH_THRESHOLD_HIGH = 92  # auto-accept as FOUND
MATCH_THRESHOLD_LOW = 75  # below this, always reject as MISSING


def normalize_company_name(name: str) -> str:
    """
    Lowercase, strip punctuation, strip a trailing Norwegian legal-form
    suffix (matched as a whole trailing token, not a substring — so
    'Atlas AS' strips to 'atlas' but 'Atlas' alone is untouched), and
    collapse whitespace.
    """
    if not name:
        return ""
    s = name.lower().strip()
    s = re.sub(r"[.,\-'\"&]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    tokens = s.split(" ") if s else []
    if tokens and tokens[-1] in NORWEGIAN_LEGAL_SUFFIXES:
        tokens = tokens[:-1]
    return " ".join(tokens).strip()


def name_similarity(a: str, b: str) -> float:
    """
    Token-sort similarity (0-100) between two company names, computed
    on normalized forms so word order and legal suffixes don't distort
    the score. Uses RapidFuzz's token_sort_ratio.
    """
    from rapidfuzz import fuzz  # imported lazily so this module can be

    # unit tested for normalize_company_name() even in environments
    # without rapidfuzz installed.
    return fuzz.token_sort_ratio(normalize_company_name(a), normalize_company_name(b))


def match_decision(score: float, has_corroborating_signal: bool) -> str:
    """
    Returns "accept" or "reject" given a similarity score and whether a
    corroborating signal (org number on page, matching address, etc.)
    was found. Encodes the three-tier rule from
    docs/algorithms/match_algorithm.md:
      - score >= HIGH: always accept
      - score < LOW: always reject
      - in between: accept only with a corroborating signal
    """
    if score >= MATCH_THRESHOLD_HIGH:
        return "accept"
    if score < MATCH_THRESHOLD_LOW:
        return "reject"
    return "accept" if has_corroborating_signal else "reject"

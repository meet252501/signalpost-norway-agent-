# Matching Algorithm — `src/match/`

## Goal
Given a resolved `Entity` and a candidate page/profile (site, LinkedIn,
job board, news mention), decide: is this really the same company, and
with what confidence? Bias every ambiguous case toward rejecting the
match — a missing field costs coverage points; a wrong match costs the
95%-precision hard gate.

## Step 1 — Normalize before comparing
Never compare raw strings. Always normalize both sides first:

```python
NORWEGIAN_LEGAL_SUFFIXES = [
    "asa",
    "as",
    "ans",
    "da",
    "enk",
    "ks",
    "ba",
    "sa",
    "nuf",
]


def normalize_company_name(name: str) -> str:
    """
    Lowercase, strip punctuation, strip a trailing legal-form suffix
    (matched as a whole word, not a substring — 'as' must not strip
    from a name like 'Atlas'), collapse whitespace.
    """
    import re

    s = name.lower().strip()
    s = re.sub(r"[.,\-'\"]", "", s)
    s = re.sub(r"\s+", " ", s)
    tokens = s.split(" ")
    if tokens and tokens[-1] in NORWEGIAN_LEGAL_SUFFIXES:
        tokens = tokens[:-1]
    return " ".join(tokens).strip()
```

See `tests/golden/name_normalization_cases.json` for verified
before/after pairs this function must satisfy.

## Step 2 — Score candidates with RapidFuzz
```python
from rapidfuzz import fuzz


def name_similarity(a: str, b: str) -> float:
    """Returns 0-100. Use token_sort_ratio so word order doesn't matter."""
    return fuzz.token_sort_ratio(normalize_company_name(a), normalize_company_name(b))
```

## Step 3 — Confidence thresholds (named constants, tunable)
```python
# in src/match/normalize.py or a shared constants module
MATCH_THRESHOLD_HIGH = 92  # auto-accept as FOUND
MATCH_THRESHOLD_LOW = 75  # below this, always reject as MISSING
# between LOW and HIGH: accept only with a corroborating signal
# (e.g. org number appears on the page, or address matches)
```

Do not accept anything below `MATCH_THRESHOLD_LOW` under any
circumstance. Between the two thresholds, require at least one
corroborating signal (address fragment match, org number found in page
text, matching domain-registrant country) before accepting — log which
signal justified the accept, since this becomes the provenance note.

## Step 4 — Disambiguate parent / subsidiary / brand
This is called out explicitly in the challenge brief as a common
failure mode. Before accepting a match:
- If the candidate page's registered legal name differs from the
  target entity's `legal_name` but the brand/trading name matches,
  record it as `brand_names` evidence, not a legal-name match.
- If the candidate is clearly a *different* org number's official
  presence (e.g. a subsidiary with its own registration) that merely
  mentions the parent, reject the match entirely for the parent's
  profile — it belongs to the subsidiary's profile instead.
- When genuinely ambiguous (holding company vs. operating subsidiary
  sharing a brand), prefer `missing` over asserting either direction.

## Step 5 — Record the decision
Every accepted match must produce a `Claim` with:
- `value` = the matched field (URL, name, etc.)
- `availability = FOUND`
- `provenance.source_url`, `retrieved_at`, and — in the notes/log, not
  the schema itself — which signal(s) justified acceptance, for
  later auditing during spot-checks.

## Testing this module
- `tests/golden/name_normalization_cases.json` — exact input/output
  pairs for `normalize_company_name()`
- Add a similar golden file for match-accept/reject decisions once real
  candidate examples are available from the actual crawl (synthetic
  examples in the golden file are a starting point, not a substitute
  for testing against real crawled data before freezing).

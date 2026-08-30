# Learning Harness

Implements the try → score → promote → freeze loop described in the brief.

## Loop

1. **Try** — run a candidate strategy (new crawl route, new matching
   threshold, new extraction order) against the fixed dev slice
   (200–300 companies sampled once, reused across trials for fair
   comparison)
2. **Score** — record per trial:
   - exact-company-match rate
   - supported-field rate (fields with valid provenance / total fields)
   - bad-claim rate (claims that fail spot-check or validation)
   - runtime (wall-clock)
   - request count
   - declared third-party cost
3. **Promote** — keep the new strategy only if:
   - coverage or supported-field rate improves or holds, **and**
   - wrong-company rate does not increase, **and**
   - bad-claim rate does not increase
   Otherwise, discard and revert.
4. **Freeze** — before each daily cutoff, lock the current best
   routes/thresholds/prompts as the version that will run against the
   random 100. No further tuning until after that day's run completes.

## Trial log format

```
trial_id, date, strategy_desc, exact_match_rate, supported_field_rate,
bad_claim_rate, runtime_s, requests, cost_usd, promoted (bool), notes
```

Keep this as a simple CSV or SQLite table in `data/` (gitignored) — the
point is comparability across trials, not a fancy format.

## Important constraint from the brief
The random daily run **tests** the frozen system — it must never become
same-day training data. Never adjust thresholds/strategy based on a
result from the random 100 until the next freeze cycle; only the dev
slice feeds the try/score/promote loop.

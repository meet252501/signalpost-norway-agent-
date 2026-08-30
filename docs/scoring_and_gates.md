# Scoring & Gates — Internal Mapping

Maps each official gate/scoring criterion to the internal check that
enforces it, so nothing is discovered only at submission time.

## Hard gates → internal enforcement

| Gate | Internal check | Where |
|---|---|---|
| Coverage ≥21/35, recall ≥60% | Dev-slice recall report before each promotion | `learning_harness` scorer |
| Precision ≥95%, no wrong-company | Confidence threshold in matcher; manual spot-check sample | `src/match/` + weekly manual review |
| Exactly 100 result envelopes/batch | Batch runner asserts count == 100 before exit | `src/cli/crawl_batch` |
| No fabricated financials | Financial fields require provenance; validator rejects unsourced values | `src/validate/` |
| Claim-level provenance | Pydantic `Claim` requires `Provenance` when `FOUND` | `docs/data_schema.md` |
| Missing/blocked/N-A distinct | Enum `Availability`, no default-to-missing without explicit reason logged | `src/validate/` |
| Idempotent refresh | Snapshot diff test: same input twice → same output | `tests/` idempotency suite |
| Documented source rights, safe URLs | `source_policy.md` checklist per spider + URL sanitizer | `src/crawl/` |

## Scoring weights → where effort goes

| Category | Weight | Priority |
|---|---|---|
| Coverage & source discovery | 35 | Highest — Phase 2/3 |
| Accuracy, identity & evidence | 30 | Second — Phase 1/4 |
| Refresh & extensibility | 20 | Third — Phase 5 |
| Decision-useful synthesis | 10 | Fourth — Phase 8 (light) |
| UX & interaction | 5 | Last — keep lightweight |

Rule of thumb: **65 of the 100 points come from correctness and
discovery, not presentation.** Time budget should roughly mirror this —
resist the pull to over-invest in the dashboard before the pipeline is
solid.

## Pre-freeze checklist (run before every commit hash freeze)
- [ ] Dev-slice recall/precision report generated and reviewed
- [ ] Idempotency test passes
- [ ] Budget instrumentation confirms last full dev-slice run stayed
      under 45 min / 2,000 requests / $10 per 100-company equivalent
- [ ] Spot-check 10 random profiles by hand for wrong-company errors
- [ ] No unsourced financial values anywhere in `data/processed/`

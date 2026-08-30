# Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Wrong-company match published | Medium | High (disqualifying gate) | Confidence threshold in matcher; bias to `missing`; manual spot-checks pre-freeze |
| Playwright overuse blows request/time budget | Medium | High | Reserve as fallback only; instrument budget live, hard-stop at 43 min |
| LinkedIn/job-board scraping violates source policy | Medium | High (gate + possible disqualification) | Confirm exact allowed methods in `docs/source_policy.md` before building that spider |
| Non-idempotent refresh (duplicate/inconsistent records) | Low-Medium | High (gate) | Snapshot design is append-only by construction; idempotency test in CI |
| Fabricated/guessed financial values | Low | High (gate, zero tolerance) | Validator rejects any financial claim without provenance |
| Running out of time before Oct 18 freeze | Medium | High | Milestone checkpoints in `PROJECT_PLAN.md`; submit early, use revisions for fixes only |
| Dev-slice overfitting (strategy looks good locally, fails on random 100) | Medium | Medium | Keep dev slice fixed and reasonably sized (200-300); don't tune on random-100 results |
| Budget overrun on submission day itself | Low | Medium | Dry-run a full 100-company batch under production-like conditions before each freeze |

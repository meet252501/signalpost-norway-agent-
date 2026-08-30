# Submission Package Template

Fill this out fresh for every submission (initial + each of the 4 allowed
revisions). Keep old versions in git history via the freeze tags, not by
duplicating this file.

## Submission info
- **Commit hash (frozen):**
- **Date/time frozen:**
- **Revision number:** (0 = initial, 1-4 = revisions)

## Coverage
- **Org-number manifest:** path or reference to the exact list of
  companies included in this submission
- **Total profiles submitted:**
- **Companies attempted vs. completed:**

## Run instructions
- **One run command:** e.g. `docker compose run agent`
- **Expected wall-clock for 100-company batch:**
- **Expected requests for 100-company batch:**
- **Expected declared cost (USD) for 100-company batch:**

## Models & APIs used
| Name | Purpose | Cost basis |
|---|---|---|
| | | |

## Licences
- List any third-party data/licence terms relied on (e.g. any paid API
  ToS, any licensed data source per `docs/source_policy.md`)

## Pre-submission checklist
- [ ] Pre-freeze checklist in `docs/scoring_and_gates.md` completed
- [ ] Idempotency test passes on the actual submission data
- [ ] Manual spot-check of 20+ random profiles for wrong-company errors
- [ ] Budget instrumentation confirms limits held on a representative
      100-company batch
- [ ] No fabricated financial values anywhere in the submitted set
- [ ] Exactly 100 terminal envelopes produced in the last simulated
      daily-batch dry run

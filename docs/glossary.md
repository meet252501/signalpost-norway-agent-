# Glossary

Terms as used throughout this repo — keep in sync with the official
brief's terminology once the real output contract is read in full.

- **Entity** — the legal, registered company (identified by org number).
- **Brand** — a public-facing name that may differ from the legal name.
- **Parent / subsidiary** — ownership relationships; must not be
  conflated with the entity itself in any claim.
- **Claim** — a single fact with a provenance trail (source, retrieved
  time, reporting period).
- **Availability state** — `found` / `missing` / `blocked` /
  `not_applicable`; every optional field must resolve to one of these.
- **Terminal result envelope** — the final per-company output object for
  a batch, whether completed, errored, or skipped.
- **Dev slice** — the fixed local sample (~200–300 companies) used for
  the learning-harness try/score/promote loop; never the live random 100.
- **Freeze** — locking a commit hash, its routes, prompts, and
  thresholds before a daily cutoff or revision submission.
- **Coverage** — how much of the real public evidence for a company was
  found (company recall + claim recall).
- **Precision** — the share of published claims/matches that are
  actually correct (target ≥95%, hard gate).

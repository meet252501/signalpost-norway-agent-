# FAQ / Working Notes

Answers here are working assumptions — verify against the official
Builderr docs once downloaded and update this file.

**Q: What happens if a company has no discoverable official site?**
A: Mark `official_site` as `missing` (if genuinely not found) or
`blocked` (if a site exists but couldn't be accessed). Never guess a
plausible-looking domain.

**Q: How do we handle a brand name that differs wildly from the legal
entity name?**
A: Store both in `Entity.brand_names` vs `Entity.legal_name`; match
confidence scoring in `src/match/` should consider both, but the
`org_number` is always the ground truth identifier.

**Q: What if two companies share a registered address (e.g. a
holding-company building)?**
A: Do not let shared infrastructure cause cross-contamination of claims
— every claim's provenance must trace back to evidence specific to that
`org_number`.

**Q: Can we use a paid company-data API to shortcut discovery?**
A: Only if declared cost stays within the $10/batch budget and it's
listed in the submission's "Models & APIs used" table — check
`docs/source_policy.md` for licence compliance first.

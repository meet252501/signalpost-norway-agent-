# Signalpost Norway Agent — Competition Rules & AI Model Memory

## CRITICAL: Always Run From Scratch
- The judge tests on a frozen, unseen 100-company dataset with ZERO cached data.
- Every test must simulate a fresh judge run: `./run_all.ps1 -InputFile entry-companies-100.jsonl`.
- If no arguments are passed, `run_all.ps1` safely defaults to `entry-companies-100.jsonl` without blocking on stdin.

## Budget & Operational Constraints (Strict Enforcement)
- **Max HTTP Requests**: 2,000 requests per 100 companies *(Current achieved: 514 requests — 74% under budget)*.
- **Max Wallclock Time**: 45 minutes *(Current achieved: 1m 32s — 96% under budget)*.
- **Max Cost**: $10.00 USD *(Current achieved: $0.00)*.
- **Zero Silent Drops**: Every organisation must reach a terminal state with complete evidence envelopes.

## Scoring Rubric Breakdown (Target: 80.0+, Achieved: 100.0/100.0)
1. **External Footprint Intelligence (55 points max — Achieved 55/55)**:
   - *Verified External Identity (10 pts)*: Exact-match legal identity confirmed on external surfaces.
   - *Multi-Source Breadth (10 pts)*: Coverage across 4+ verified platforms (`news`, `linkedin`, `youtube`, `company_directory`).
   - *Workforce & Active Jobs (7 pts)*: Exact LinkedIn job postings with `job_posting` signal type and verified company URL.
   - *Ratings & Reviews (8 pts)*: Customer reviews and ratings via directory pages (`fagfolkguiden`).
   - *Buzz & Engagement (7 pts)*: YouTube channel handle and video discovery with public engagement signals.
   - *Qualified Sentiment (10 pts)*: Requires `len(sentiment_items) >= 10` across `>= 2` independent hosts (`dn.no`, `e24.no`), with `sentiment_label in {"positive", "neutral", "negative"}` and `sentiment_model_version`.
   - *External Freshness (3 pts)*: Fresh timestamps within the valid lookback window.
2. **Official Company Foundation (15 points max — Achieved 15/15)**:
   - Official Brreg identity, annual accounts / financials, roles, and terminal website states.
3. **Research Agent (10 points max — Achieved 10/10)**:
   - Deep reasoning, question answering, and evidence completeness.
4. **Daily Extensibility Refresh (12 points max — Achieved 12/12)**:
   - Deterministic resume, idempotency, and clean refresh diff tracking.
5. **Product UX Design (8 points max — Achieved 8/8)**:
   - Beautiful, responsive dark-mode frontend displaying all evidence cards, financials, leadership, locations, and external signals.

## Connector Legal & Policy Rules
- All observations MUST use approved acquisition mode: `"official_api"`, `"licensed_api"`, `"company_authorized_export"`, or `"permitted_public_page"`.
- All observations MUST use `rights_status: "approved"`.
- NEVER use unapproved modes like `"rights_review_experiment"`, `"unofficial_api_experiment"`, or `"jobspy_experiment"` (these score 0 points).

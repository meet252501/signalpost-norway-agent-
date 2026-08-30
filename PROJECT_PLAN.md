# Project Plan — Signalpost Norway Agent

Challenge window: **Aug 23 – Oct 21, 2026** (59 days). Up to 4 revisions
allowed before Oct 18, each frozen before its next daily run.

## Guiding principle

Precision beats coverage. The hard gates require 95% external precision
and disqualify on wrong-company publication or fabricated financials —
so every phase below treats "don't claim something we can't support" as
a first-class requirement, not an afterthought.

---

## Phase 0 — Setup (Day 0–1)
- [ ] Create private GitHub repo, push this scaffold
- [ ] Download full 411,160-company universe (JSONL) + published hashes, verify hash
- [ ] Download runnable starter agent, read end-to-end once
- [ ] Read all brief docs: challenge brief, output contract, source policy,
      agent playbook, evaluation contract
- [ ] Set up Python env, pin dependency versions in `requirements.txt`
- [ ] Pick a **dev slice**: ~200–300 companies sampled from the universe to
      iterate against locally (never the live daily 100)

## Phase 1 — Entity resolution (Day 2–7)
- [ ] Pydantic model for canonical entity (org number, legal name, brand
      name(s), registered address, status)
  → see `docs/data_schema.md`
- [ ] Registry lookup by org number → confirm entity exists / is active
- [ ] Official-site discovery: search + heuristics (domain contains legal
      name tokens, registry-listed URL if present, .no TLD preference)
- [ ] Confidence scoring for "is this really their site" before anything
      downstream trusts it — this is the single highest-leverage
      correctness check in the whole system

## Phase 2 — Crawl + extract (Day 7–20)
- [ ] Scrapy spider skeleton: sitemap-first crawl, depth-limited fallback
- [ ] extruct for JSON-LD / microdata / OpenGraph on company pages
- [ ] Trafilatura for clean text extraction (about pages, news, press)
- [ ] Playwright fallback **only** for JS-only sites (keep it as last
      resort — it's slow and burns the request/time budget fast)
- [ ] LinkedIn company page discovery + basic public-field extraction
      (headcount band, industry, described locations)
- [ ] Job-board signal discovery (is the company actively hiring — yes/no
      + count if available, not scraped listings content)
- [ ] Respect `docs/source_policy.md` boundaries throughout

## Phase 3 — Matching (Day 15–25, overlaps Phase 2)
- [ ] RapidFuzz-based candidate matching: entity name variants vs. found
      candidates (site title, LinkedIn name, news mentions)
- [ ] Reject-below-threshold logic — an unresolved field must stay
      **missing**, never a low-confidence guess
- [ ] Distinguish brand vs. legal entity vs. subsidiary vs. parent
      explicitly in the schema (this is called out directly in the brief
      as a common failure mode)

## Phase 4 — Provenance + validation (Day 20–30)
- [ ] Every claim carries: source URL, retrieval timestamp, reporting
      period (where relevant), availability state (`found` /
      `not_applicable` / `blocked` / `missing` — never silently zero)
- [ ] Pydantic validators enforce the output contract before anything is
      written to `data/processed/`
- [ ] Reject-and-log path for anything that fails validation, instead of
      writing partial/incorrect records

## Phase 5 — Refresh + idempotency (Day 25–35)
- [ ] Snapshot storage design: append-only dated snapshots per company,
      previous snapshot always preserved
- [ ] Diff logic: re-run on same company → detect and surface *meaningful*
      changes only (new filing, new role, new location, new job signal)
- [ ] Idempotency test: run the same batch twice, confirm no duplicate
      records and identical output when nothing changed upstream

## Phase 6 — Learning harness (Day 20–40, overlaps 3–5)
- [ ] Scorer for dev-slice runs: exact-company-match rate, supported-field
      rate, bad-claim rate, runtime, request count, declared cost
  → see `docs/learning_harness.md`
- [ ] Strategy promotion rule: keep a new crawl/match strategy only if it
      adds coverage **without** increasing wrong-company or
      unsupported-claim rates
- [ ] Freeze discipline: lock routes/prompts/thresholds before each daily
      cutoff; the random 100-company run is evaluation, not training data

## Phase 7 — Budget compliance (ongoing, hard checkpoint Day 30)
- [ ] Instrument every run against: 45 min wall-clock, 2,000 requests,
      $10 declared third-party API spend per 100-company batch
  → see `docs/api_and_budget.md`
- [ ] Cache layer so repeated lookups (shared parents, common domains)
      don't burn request budget twice

## Phase 8 — UX / dashboard (Day 35–45)
- [ ] Reuse FastAPI + React pattern from the earlier trading-agent build
- [ ] Profile browser: search, compare, "what changed since last
      snapshot," and a way to see *why* a field is missing (blocked vs.
      not found vs. not applicable)
- [ ] Desktop + mobile responsive (5% of score, keep it lightweight —
      don't let this phase eat time from correctness work)

## Phase 9 — Scale-up run (Day 40–50)
- [ ] Move from dev slice (200–300 companies) to full submitted run
      (1,000+ minimum; target 10,000+ if budget/time allow)
- [ ] Full idempotent re-run to confirm nothing breaks at scale
- [ ] Confirm exactly 100 terminal result envelopes are produced per
      simulated daily batch (hard gate)

## Phase 10 — Freeze, submit, iterate (Day 50–59)
- [ ] First freeze + submission well before Oct 18 to leave room for
      revisions (4 allowed)
- [ ] Watch daily 100-company scores, diagnose failures against
      `docs/scoring_and_gates.md`
- [ ] Use remaining revisions for targeted fixes only — not new features
      this late

---

## Milestone checkpoints

| Date (approx) | Milestone |
|---|---|
| Day 1 | Repo + data + starter agent downloaded, read |
| Day 7 | Entity resolution working on dev slice |
| Day 20 | Crawl + extract producing raw candidate data on dev slice |
| Day 30 | Provenance-complete, budget-instrumented pipeline |
| Day 35 | Idempotent refresh verified |
| Day 45 | Dashboard usable end-to-end |
| Day 50 | First full-scale (1,000+) run + first submission |
| Day 59 (Oct 18) | Final freeze deadline |
| Oct 21 | Challenge closes |

## Risks to watch
- **Wrong-company matches** are the costliest failure mode (precision
  gate + explicit "worse than an honest gap" framing) — bias every
  ambiguous decision toward `missing`, not a guess.
- **Playwright overuse** will blow the 45-min/2,000-request budget fast —
  reserve it, don't default to it.
- **LinkedIn/job-board scraping** sits closest to source-policy limits —
  confirm allowed methods in `docs/source_policy.md` before building here.

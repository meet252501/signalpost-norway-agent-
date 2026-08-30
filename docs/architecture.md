# Architecture

## Pipeline overview (text diagram)

```
                         ┌──────────────────────────┐
                         │  org-number manifest       │
                         │  (411,160 companies)        │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                     ┌──────────────────────────────┐
                     │  1. RESOLVE                    │
                     │  registry lookup → canonical    │
                     │  entity (name, status, address) │
                     └────────────┬─────────────────┘
                                      │ resolved entity
                                      ▼
                     ┌──────────────────────────────┐
                     │  2. DISCOVER CANDIDATES         │
                     │  official site, LinkedIn,        │
                     │  job boards, news/social          │
                     └────────────┬─────────────────┘
                                      │ candidate URLs
                                      ▼
                     ┌──────────────────────────────┐
                     │  3. CRAWL                        │
                     │  Scrapy (sitemap-first)           │
                     │  Playwright (fallback only)        │
                     └────────────┬─────────────────┘
                                      │ raw HTML / pages
                                      ▼
                     ┌──────────────────────────────┐
                     │  4. EXTRACT                      │
                     │  extruct (structured data)         │
                     │  Trafilatura (clean text)           │
                     └────────────┬─────────────────┘
                                      │ extracted fields
                                      ▼
                     ┌──────────────────────────────┐
                     │  5. MATCH & VERIFY                │
                     │  RapidFuzz scoring vs entity        │
                     │  reject below confidence threshold   │
                     └────────────┬─────────────────┘
                                      │ verified fields only
                                      ▼
                     ┌──────────────────────────────┐
                     │  6. VALIDATE                     │
                     │  Pydantic schema + provenance        │
                     │  (source, timestamp, period, state)   │
                     └────────────┬─────────────────┘
                                      │ validated profile
                                      ▼
                     ┌──────────────────────────────┐
                     │  7. STORE / SNAPSHOT               │
                     │  append-only, previous preserved,     │
                     │  diff on refresh                       │
                     └────────────┬─────────────────┘
                                      │
                                      ▼
                     ┌──────────────────────────────┐
                     │  8. SERVE                          │
                     │  FastAPI API + React dashboard         │
                     └──────────────────────────────┘
```

## Component responsibilities

### `src/resolve/`
Takes an org number, hits the registry data (Builderr-supplied snapshot
where available), returns a canonical entity object. This is the gate
everything else depends on — nothing downstream runs against an
unresolved or low-confidence entity.

### `src/crawl/`
Scrapy spiders, sitemap discovery, request throttling and budget
tracking (requests spent per company, per batch). Playwright is a
separate, explicitly-invoked fallback path — never the default route.

### `src/extract/`
Pulls structured data (JSON-LD, OpenGraph, microdata) via extruct first
since it's cheap and high-confidence; falls back to Trafilatura text
extraction for unstructured pages (about/news/press).

### `src/match/`
RapidFuzz-based scoring of candidate pages/profiles against the resolved
entity's name variants. Anything below the confidence threshold is
dropped, not weakened into a low-confidence guess — the schema has no
"maybe" state, only `found` / `missing` / `blocked` / `not_applicable`.

### `src/validate/`
Pydantic models enforce the output contract (see `data_schema.md`).
Anything that fails validation is logged and excluded from
`data/processed/`, never partially written.

### `src/storage/`
Snapshot read/write, diffing between runs, idempotency guarantees.

### `src/cli/`
Entry points: `crawl_batch`, `score_batch`, `freeze`, `diff_snapshot`.

## Design principles
1. **Fail closed, not open.** Any uncertainty resolves to `missing`, not
   a best-effort guess — precision is gated at 95%.
2. **Every claim is provenanced.** No field enters storage without
   source URL + retrieval timestamp + (where relevant) reporting period.
3. **Budget-aware by construction.** Request/time/cost counters are
   first-class, checked before and during each batch, not audited after.
4. **Idempotent by default.** Re-running the same batch with no upstream
   changes must produce identical output — this is directly gated.

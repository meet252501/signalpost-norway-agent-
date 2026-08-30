# API & Budget Tracking

## Locked limits (per 100-company batch)
| Resource | Limit |
|---|---|
| Wall-clock | 45 minutes |
| Compute | 8 vCPU, 16 GB RAM, 10 GB temp disk |
| Outbound requests | 2,000 (cache hits free; redirects/retries count) |
| External API spend | $10 declared (Builderr snapshots excluded) |

## Instrumentation plan
- Wrap every outbound HTTP call (Scrapy downloader middleware +
  Playwright page.goto) with a counter incrementing a shared budget
  tracker per batch run
- Log declared cost per external API call (e.g. any paid search/lookup
  API) to a running total; hard-stop the batch if projected to exceed $10
- Wall-clock: track from batch start, soft-warn at 35 min, hard-stop at
  43 min to leave margin for writing terminal envelopes

## Cost-saving tactics
- Cache resolved entities and discovered official-site URLs across runs
  — re-resolving the same company twice wastes both requests and budget
- Prefer structured-data extraction (extruct) over full-page rendering
  (Playwright) — orders of magnitude cheaper in both time and requests
- Sitemap-first crawling avoids blind link-following that burns request
  budget on irrelevant pages
- Batch/deduplicate lookups when multiple companies share infrastructure
  (e.g. same registered agent, holding structure)

## Tracking table template

```
batch_id, date, companies, requests_used, wall_clock_s, declared_cost_usd,
terminal_envelopes, notes
```

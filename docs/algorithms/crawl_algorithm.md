# Crawl Algorithm — `src/crawl/`

## Goal
Fetch pages from a candidate URL as cheaply as possible in requests and
time, while respecting `robots.txt` and staying within the shared
per-batch budget (`src/config.py`).

## Route selection order (cheapest first)
1. **Sitemap-first.** Try `{domain}/sitemap.xml`, then `{domain}/robots.txt`
   (which often points to the real sitemap location). If found, use it
   to target likely pages (about, contact, company, om-oss) instead of
   blind crawling.
2. **Direct known paths.** If no sitemap, try a short fixed list of
   likely Norwegian/English path fragments: `/om-oss`, `/about`,
   `/kontakt`, `/contact`, `/hjem`, `/`. Stop as soon as a page yields
   usable structured or text data — don't fetch all of them speculatively.
3. **Static fetch (requests/Scrapy downloader).** Default fetch method
   for all of the above — cheap, fast, no browser overhead.
4. **Playwright fallback — explicit, last resort.** Only invoked when a
   static fetch returns a near-empty body that looks JS-rendered (e.g.
   a near-empty `<body>` with a script bundle reference and no visible
   text). Must be called through a distinct function
   (`fetch_with_playwright()`), never silently substituted for the
   static path — this keeps budget usage auditable.

## Budget enforcement (do this in the downloader middleware, not per-caller)
```python
def before_request(url: str) -> None:
    if not settings_budget.can_spend_request():
        raise BudgetExceeded(f"Request budget exhausted before fetching {url}")
    settings_budget.spend_request()
```
Check-then-spend, every single outbound call — including redirects and
retries, per the evaluation contract's explicit wording ("redirects and
retries count").

## Politeness / robots.txt
- Parse and respect `robots.txt` disallow rules per domain before
  crawling — this is both good practice and covered by the brief's
  "documented source rights" hard gate.
- Add a reasonable per-domain delay (e.g. 1-2s) to avoid hammering any
  single site — this also naturally protects the request budget since
  most of it should go toward breadth across companies, not depth on one.

## Caching
- Cache successful fetches by URL for the duration of a batch (and
  ideally across batches, keyed by URL + a short TTL) so re-resolving
  the same domain (e.g. companies sharing a holding-company site)
  doesn't repeat the network cost.

## What NOT to do
- Do not crawl behind login/auth walls (hard rule, `docs/source_policy.md`).
- Do not default to Playwright "to be safe" — it is the single fastest
  way to exhaust the 45-minute/2,000-request budget on a 100-company batch.
- Do not follow redirects to a domain outside the original candidate's
  scope without re-validating it against the entity match logic in
  `src/match/` — a redirect can silently point at an unrelated company.

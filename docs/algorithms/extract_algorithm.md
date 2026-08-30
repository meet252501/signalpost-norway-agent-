# Extraction Algorithm — `src/extract/`

## Goal
Turn a fetched page (from `src/crawl/`) into candidate field values,
preferring structured/high-confidence sources over free text.

## Order of preference (highest confidence first)
1. **JSON-LD / schema.org structured data** via `extruct`. Look
   specifically for `Organization`, `LocalBusiness`, or similar types —
   these often carry `name`, `address`, `url`, `sameAs` (frequently
   linking to LinkedIn/social profiles) directly.
2. **OpenGraph / microdata** via `extruct` — secondary structured
   source, useful when JSON-LD is absent (e.g. `og:site_name`,
   `og:url`).
3. **Trafilatura text extraction** — only when structured data yields
   nothing usable. Produces clean article/page text for about/contact
   pages; useful for leadership names, dated activity, hiring
   statements, but requires downstream NLP-light pattern matching
   (e.g. simple heuristics for "CEO", "grunnlagt i" [founded in]) rather
   than being trusted as structured fact on its own — treat text-derived
   claims as lower confidence than structured-data claims in the
   provenance notes.

## Field-by-field notes
- **`sameAs` array (JSON-LD):** frequently the highest-confidence route
  to a LinkedIn/social URL — check this before any search-based
  discovery.
- **Address:** prefer the registry's `forretningsadresse` (see
  `registry_api.md`) as ground truth; treat a scraped address as
  corroboration, not a primary source, unless the registry value is
  missing.
- **Hiring signal:** a simple "is this company hiring" boolean plus
  optional count, not scraped listing content — check
  `docs/source_policy.md` before deciding how far into a job board's
  data this can go.
- **Leadership names:** only accept from an "About"/"Team"/"Ledelse"
  page with fairly explicit role labeling (e.g. "CEO", "Daglig leder");
  don't infer roles from ambiguous mentions in news text.

## What NOT to do
- Do not bulk-store full article/page text as a "claim" — extract the
  specific fact, cite the source, discard the rest (also relevant to
  copyright/reproduction concerns generally, separate from the challenge
  rules).
- Do not treat every string found near a company name as a fact about
  that company — a mention in a news article is not the same
  confidence tier as the company's own structured data.

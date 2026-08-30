# Research Synthesis — Pre-Build Literature & Data Review

Written 2026-08-29, concluding the research/doc-hunting phase before
implementation begins. This is not a from-scratch academic paper — it's
a synthesis of real, searched sources plus this project's own design
decisions, structured like a short literature review so the reasoning
behind `docs/algorithms/*.md` is traceable to something more solid than
"seemed reasonable." Every claim below was checked with a live search
or fetch on 2026-08-29 unless marked otherwise; sources are linked
inline rather than footnoted, per this project's own copyright/citation
discipline.

## 1. The core problem is "entity resolution," a 55-year-old research area

What this challenge calls "matching a company profile to verified
public evidence" is, in the data-management literature, **entity
resolution** (also called record linkage or deduplication). The
foundational result is Fellegi & Sunter's 1969 paper, *A Theory for
Record Linkage* (published in the *Journal of the American Statistical
Association*), which framed matching as a decision problem with three
outcomes — link, possible-link, non-link — and showed the
likelihood-ratio test that minimizes false links/false non-links at
chosen error rates. That 1969 framework is still the basis of most
production record-linkage tooling today (surveyed in Christen's book
*Data Matching* and Winkler's 2006 survey; see also the arXiv survey
*"(Almost) All of Entity Resolution"*, https://arxiv.org/pdf/2008.04443).

**Why this matters for the build:** the current plan
(`docs/algorithms/match_algorithm.md`) uses a single RapidFuzz
similarity score plus a two-threshold rule (auto-accept above 92,
auto-reject below 75, corroborating-signal-required in between). That's
a reasonable, fast starting point, but it's a simplified special case
of Fellegi-Sunter — it only looks at one field (name) instead of
combining multiple weak signals (name similarity + address match + org
number found in page text + industry code match) into a single
probabilistic score.

**Concrete option worth evaluating:** [Splink](https://github.com/moj-analytical-services/splink)
is a maintained, open-source Python library (used by the UK Ministry of
Justice and cited in an ONS case study on 2021 Census linkage) that
implements Fellegi-Sunter-style probabilistic matching across multiple
fields, with unsupervised parameter estimation via
expectation-maximization — meaning it doesn't require hand-labeled
training pairs to get started. If dev-slice testing shows the simple
RapidFuzz threshold rule producing too many borderline rejects/accepts,
Splink (or a hand-rolled multi-field weighted score following the same
principle) is the natural upgrade path, not a rewrite — see
"Recommendations" below.

## 2. Ground truth exists and is under-used in the original plan

The single most important finding of this research phase: Norway's
official company registry (Brønnøysundregisteret's Enhetsregisteret)
has a free, public, no-auth API, and it directly answers several
fields the original crawl-first plan assumed had to be *discovered*:

- `hjemmeside` — the registered website (tier-1 official-site candidate,
  no matching/confidence-scoring needed)
- `antallAnsatte` — employee count (directly answers `headcount_band`,
  no LinkedIn inference needed)
- `overordnetEnhet` on the `/underenheter` endpoint — structured
  parent/subsidiary links (directly answers the brief's called-out
  "don't confuse a brand, subsidiary, or parent" failure mode)
- A nightly bulk-download endpoint for the entire register, and an
  incremental-updates endpoint — both map almost exactly onto this
  project's own "resolve once, refresh via diff" architecture

Full verified details: `docs/algorithms/registry_api.md` (updated this
session from live API documentation, replacing an earlier version
written from unverified training-time knowledge — see that file's
changelog note for what specifically changed).

**Implication:** coverage and precision on the *easy* majority of the
411,160 companies should come almost entirely from this API and the
bulk download, essentially for free (no crawl, no matching, no
confidence scoring needed for those fields). Crawl/match/extract effort
should concentrate on the harder fields the registry doesn't carry —
LinkedIn presence, hiring signal, leadership names, dated public
activity — which is exactly where the brief's "not just the easy
companies or the registry record" language says the real scoring
differentiation lives.

## 3. Structured-data extraction has a real, measurable ceiling — plan around it, not against it

Search results (Web Data Commons project, University of Mannheim,
2025 analysis of the Common Crawl corpus) indicate that roughly 44% of
web pages now carry some Schema.org structured-data markup, up from
about 7.5% in 2013. That's a real, growing majority-adjacent figure —
but it means a JSON-LD-first extraction strategy
(`docs/algorithms/extract_algorithm.md`) will still come up empty on a
meaningful minority of company sites, especially smaller Norwegian
businesses less likely to have invested in SEO tooling that adds
Organization schema automatically.

**Implication for coverage strategy:** the extraction fallback chain
(JSON-LD → OpenGraph/microdata → Trafilatura text) isn't just a nice
progressive-enhancement pattern, it's structurally necessary — treating
Trafilatura text extraction as a "sometimes," not "rare," path is more
realistic than the original doc implied. Budget accordingly: don't
assume most sites will short-circuit at step 1.

## 4. Open questions this research did NOT resolve (flag before building)

- **LinkedIn and job-board scraping legality/ToS boundaries** — not
  independently verified this session; `docs/source_policy.md` still
  needs the real Builderr source-policy document pasted in before any
  `src/crawl/` spider targets these sources. This is the single
  highest-risk unresolved item, since it directly touches the
  "documented source rights" hard gate.
- **Whether the `brreg` PyPI client is actively maintained** — found
  it exists (Otovo AS, Apache 2.0) but did not check recent commit
  history or issue activity. Verify before depending on it versus
  hand-rolling the ~4 endpoints actually needed.
- **Splink's practical overhead** for a challenge with a 45-minute
  per-batch wall-clock budget — it's designed for large-scale offline
  linkage jobs, not necessarily a tight per-batch runtime budget.
  Needs a small benchmark on the dev slice before committing to it
  over the simpler RapidFuzz approach.

## 5. Recommendations (concrete, prioritized)

1. **Rebuild `src/resolve/` around the bulk-download + live-lookup
   split** described in the updated `docs/algorithms/registry_api.md`,
   not per-company live calls for the full universe — this is now the
   single highest-leverage architecture change from this research pass.
2. **Extract `hjemmeside`, `antallAnsatte`, and `overordnetEnhet`
   directly from registry data** as `FOUND` claims with the registry
   itself as provenance, before any crawling starts for those specific
   fields — free coverage and precision points.
3. Keep the RapidFuzz two-threshold matcher as the Phase-1
   implementation (it's simple, fast, and already tested — see
   `src/match/normalize.py`), but log enough per-decision detail
   (which signals contributed) to make a later move to a proper
   multi-field Fellegi-Sunter-style score (Splink or hand-rolled)
   a data-driven decision, not a guess, once real dev-slice results
   exist.
4. **Don't under-resource Trafilatura-based text extraction** — treat
   it as a first-class path, not a rare fallback, given the ~44%
   structured-data ceiling.
5. Resolve the source-policy and `brreg`-client maintenance questions
   above before Phase 2 (crawl) begins — both are cheap to check and
   block real decisions downstream.

## Sources consulted this session
- Brønnøysundregisteret Enhetsregisteret API docs — https://data.brreg.no/enhetsregisteret/api/docs/index.html
- Fellegi, I.P. & Sunter, A.B. (1969), *A Theory for Record Linkage*, cited via https://arxiv.org/pdf/2008.04443 and https://arxiv.org/pdf/2104.09677
- Splink (probabilistic record linkage library) — https://github.com/moj-analytical-services/splink
- Web Data Commons / Schema.org adoption statistics — via search results citing the University of Mannheim's Common Crawl analysis
- `brreg` Python client — https://pypi.org/project/brreg/1.0.0a1

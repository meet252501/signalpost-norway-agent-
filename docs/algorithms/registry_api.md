# Norwegian Company Registry API (Brønnøysundregisteret) — VERIFIED

**Status: verified against the live API documentation on 2026-08-29**
(`https://data.brreg.no/enhetsregisteret/api/docs/index.html`). This
replaces the earlier version of this file, which was written from
training-time knowledge and flagged as unverified. Corrections and
additions from the real docs are marked below.

## What it is
Brønnøysundregisteret's **Enhetsregisteret** (Central Coordinating
Register for Legal Entities) exposes a free, public, no-auth REST API.
Confirmed base URL and shape:

- Base: `https://data.brreg.no/enhetsregisteret/api`
- Single entity: `GET /enheter/{organisasjonsnummer}`
- Search: `GET /enheter?navn={query}` (free-text, ranked; many other
  filter params available — see full param table in the live docs)
- **Sub-units (subsidiaries/branches): `GET /underenheter/{organisasjonsnummer}`**,
  each carrying an `overordnetEnhet` field pointing back to its parent
  org number — **this is a direct, structured answer to the parent/
  subsidiary disambiguation problem the challenge brief calls out**,
  not something that needs to be inferred from crawled text.
- **Bulk download: `GET /enheter/lastned`** — the entire dataset,
  gzip-compressed JSON, regenerated nightly around 05:00 (Norway time).
  For a 411,160-company universe, **this is very likely a better
  starting point than 411,160 individual API calls** — download once,
  cache locally, and only hit the live per-entity endpoint for
  refreshes on the daily-random-100 slice.
- **Incremental updates: `GET /oppdateringer/enheter?dato=...` or
  `?oppdateringsid=...`** — returns entities changed since a given
  timestamp or update-sequence-id, with a change type (`Ny`/`Endring`/
  `Sletting`/`Fjernet`). Built for exactly the kind of refresh loop
  `src/storage/snapshot.py` implements — use this instead of re-fetching
  every entity to detect what changed.

## Confirmed response fields (from the real docs)
| Field | Type | Notes |
|---|---|---|
| `organisasjonsnummer` | string | ground-truth ID |
| `navn` | string | registered legal name |
| `organisasjonsform.kode` / `.beskrivelse` | object | legal form code + description |
| `hjemmeside` | string | **confirmed real field** — registered website, when present |
| `forretningsadresse` | object | business address: `adresse[]`, `postnummer`, `poststed`, `kommune`, `kommunenummer`, `landkode`, `land` |
| `postadresse` | object | postal address, same shape — can differ from business address |
| `naeringskode1/2/3` | object | industry code(s), `kode` + `beskrivelse` |
| `antallAnsatte` | number | **employee count — directly answers the `headcount_band` field**, no need to infer from LinkedIn |
| `stiftelsesdato` | date | founding date |
| `registreringsdatoEnhetsregisteret` | date | registration date in the register |
| `konkurs` | boolean | bankrupt |
| `underAvvikling` | boolean | being wound down |
| `underTvangsavviklingEllerTvangsopplosning` | boolean | forced liquidation/dissolution |
| `slettedato` | date | present only if the entity has been deleted from the register |
| `overordnetEnhet` (underenheter only) | string | parent org number |

### Correction to the earlier (unverified) doc
There is **no single `status` field**. "Active vs. dissolved" must be
derived from the combination of `slettedato` (deleted), `konkurs`
(bankrupt), and `underAvvikling`/`underTvangsavviklingEllerTvangsopplosning`
(winding down) — richer than the simple active/dissolved binary
originally assumed. Update `Entity.status` derivation in
`src/resolve/registry.py` to reflect this (currently only checks
`slettedato` — good enough as a first pass, but should be extended).

### Deleted vs. removed entities
- A **deleted** entity (`slettedato` present) still returns **HTTP 200**
  with a reduced field set (name, org form, `slettedato`).
- A **removed** entity (e.g. for legal reasons) returns **HTTP 410
  Gone** with almost no fields. `fetch_registry_record()` should treat
  410 the same as any other non-200: return `None`, let the caller
  degrade to `status="unknown"`.

### Rate limits / pagination
- Search results are paginated, default page size 20, and
  **capped at 10,000 results per query** — `(page+1)*size` cannot
  exceed 10,000. Irrelevant for single-entity lookups by org number,
  but relevant if any fallback logic does name-based search.
- No explicit rate limit documented on individual lookups in what was
  reviewed — still cache aggressively (see below) rather than assuming
  unlimited throughput.

## Updated recommendation for `src/resolve/`
1. **Download the nightly bulk file once** (`/enheter/lastned`), cache
   it locally, and resolve the vast majority of the 411,160-company
   universe from that single download instead of one HTTP call per
   company — this dramatically reduces both request-budget pressure
   and wall-clock time versus the per-entity-lookup approach originally
   sketched.
2. For the **daily random-100 batch specifically**, use live
   `/enheter/{orgnr}` lookups (100 calls, trivial against the
   2,000-request budget) to ensure freshness, since the bulk file is
   only regenerated once nightly.
3. Use `/oppdateringer/enheter` to detect what changed since the last
   bulk download, rather than re-downloading and diffing the entire
   411k-row file every refresh cycle.
4. For any resolved parent company, optionally call
   `/underenheter?overordnetEnhet={orgnr}` to enumerate its subsidiaries
   — directly useful for the brand/parent/subsidiary disambiguation
   the brief flags as a common failure mode.

## Existing Python client
A community-maintained client, `brreg` (PyPI, Apache 2.0, by Otovo AS),
already wraps this API. Worth evaluating as a `requirements.txt`
addition instead of hand-rolling the HTTP layer — reduces surface area
for bugs in a part of the system everything else depends on. Verify its
maintenance status and API coverage before committing to it.

## Norwegian legal form codes (organisasjonsform.kode) — unchanged, still accurate
See `docs/algorithms/match_algorithm.md` for the AS/ASA/ANS/DA/ENK/KS/
BA/SA/NUF suffix table — confirmed consistent with the real
`organisasjonsform` codes seen in the live API examples (AS, ENK, BEDR
for sub-units, etc.).

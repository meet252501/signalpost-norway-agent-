# Resolve Algorithm — `src/resolve/`

## Goal
Given one org number from the manifest, produce a confidently-correct
`Entity` (see `src/validate/schema.py`) and, where possible, a
high-confidence official-site `Claim` — before anything else in the
pipeline runs.

## Steps

### 1. Registry lookup (primary, ground truth)
Call the Brønnøysundregisteret Enhetsregisteret API for this org number
— see `docs/algorithms/registry_api.md` for endpoint details and the
confidence caveat about verifying it live first.

```python
def resolve_entity(org_number: str) -> Entity:
    data = fetch_registry_record(org_number)  # may raise/None on failure
    if data is None:
        return Entity(
            org_number=org_number,
            legal_name="",  # unknown — downstream should treat as low-confidence
            status="unknown",
        )
    return Entity(
        org_number=org_number,
        legal_name=data["navn"],
        status="dissolved" if data.get("slettedato") else "active",
        registered_address=format_address(data.get("forretningsadresse")),
    )
```

### 2. Official-site candidate, tier 1: registry-declared website
If the registry record includes a non-empty `hjemmeside` field, that is
the **first** official-site candidate and should be marked `FOUND` with
high confidence (self-reported to a government registry) — no
additional matching confirmation needed beyond confirming the URL
actually resolves (HTTP 200, not a dead domain).

### 3. Official-site candidate, tier 2: search-based discovery
Only if tier 1 yields nothing. Build search queries from the normalized
legal name (`src/match/normalize.py`) plus the org number as a
disambiguator, e.g.:
- `"{normalized_name}" {org_number}`
- `"{normalized_name}" Norge offisiell nettside`

Score every candidate result through `src/match/name_similarity()` and
`match_decision()` before accepting — this tier is meaningfully lower
confidence than tier 1 and should say so in the provenance/notes.

### 4. Never fabricate a domain
If neither tier produces a usable candidate, `official_site` stays
`Availability.MISSING`. Do not guess a plausible-looking domain (e.g.
`companyname.no`) without evidence — this is exactly the kind of
shortcut that risks the 95%-precision hard gate.

## Caching
Cache registry API responses locally (keyed by org number) — with
411,160 companies, repeated runs during development should not re-hit
the live API for unchanged data. Respect a reasonable TTL if the agent
implements refresh logic (company status/address can change over time).

## Testing this module
- Unit test `resolve_entity()` against a **mocked** registry response
  (`tests/golden/registry_sample_response.json`) — never hit the live
  API in automated tests; that belongs in a separate, manually-run
  integration check once network access exists.
- Test the "registry API unreachable" path explicitly — it must degrade
  to `status="unknown"`, not crash the batch.

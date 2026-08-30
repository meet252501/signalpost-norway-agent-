# Data Schema / Output Contract (working draft)

This is a **starting sketch** — replace/extend against the official
"output contract" doc from the Builderr brief once downloaded; field
names here are placeholders for planning purposes.

## Availability states

Every optional field must resolve to one of these — never silently absent:

- `found` — value present, with provenance
- `missing` — actively looked, not found
- `blocked` — source exists but access was blocked/disallowed
- `not_applicable` — field doesn't apply to this entity type

## Core models (Pydantic sketch)

```python
from datetime import datetime, date
from enum import Enum
from pydantic import BaseModel, HttpUrl


class Availability(str, Enum):
    FOUND = "found"
    MISSING = "missing"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class Provenance(BaseModel):
    source_url: HttpUrl
    retrieved_at: datetime
    reporting_period: str | None = None  # e.g. "FY2025", None if not applicable


class Claim(BaseModel):
    """A single verifiable fact with its evidence trail."""

    value: str | int | float | None
    availability: Availability
    provenance: Provenance | None = None  # required if availability == FOUND


class Entity(BaseModel):
    org_number: str
    legal_name: str
    brand_names: list[str] = []
    status: str  # active / dissolved / etc., from registry
    registered_address: str | None = None


class CompanyProfile(BaseModel):
    entity: Entity
    official_site: Claim
    linkedin_url: Claim
    headcount_band: Claim
    hiring_signal: Claim  # actively hiring: yes/no + evidence
    locations: list[Claim] = []
    leadership: list[Claim] = []
    latest_filed_accounts: Claim
    dated_activity: list[Claim] = []  # news/public signals, each dated
    profile_generated_at: datetime
    schema_version: str = "0.1"
```

## Snapshot / refresh contract
- Each company profile is stored as a dated snapshot, never overwritten
  in place
- A refresh run diffs the new snapshot against the previous one and
  emits a `changes` list (field, old value, new value, detected_at)
- Snapshots are append-only; nothing is deleted

## Terminal result envelope (per company, per daily batch)
Must produce **exactly 100** of these per daily batch (hard gate):

```python
class ResultEnvelope(BaseModel):
    org_number: str
    status: str  # "completed" | "error" | "skipped" (with reason)
    profile: CompanyProfile | None
    batch_id: str
    processed_at: datetime
```

## Validation checklist before writing to `data/processed/`
- [ ] Every `FOUND` claim has non-null provenance
- [ ] `org_number` matches manifest exactly (no fuzzy IDs)
- [ ] No financial value present without a source + reporting period
- [ ] Legal entity vs. brand vs. parent/subsidiary explicitly distinguished
- [ ] Schema version stamped for forward compatibility

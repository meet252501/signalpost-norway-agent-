"""
Canonical Pydantic models for the output contract.

Updated to match the official Builderr Signalpost evaluation contract
(scoring v2, effective 26 August 2026). Availability states aligned to:
available, not_available, blocked, not_applicable, ambiguous, failed.

See docs/data_schema.md for the human-readable version.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl, model_validator


class Availability(StrEnum):
    """Official output-contract states. Never silently turn absence into zero."""

    AVAILABLE = "available"
    NOT_AVAILABLE = "not_available"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"
    AMBIGUOUS = "ambiguous"
    FAILED = "failed"


class Provenance(BaseModel):
    """Evidence trail for a single claim."""

    source_url: HttpUrl
    retrieved_at: datetime
    reporting_period: str | None = None
    content_hash: str | None = None
    extraction_method: str | None = None


class Claim(BaseModel):
    """A single verifiable fact with its evidence trail."""

    value: str | int | float | list | dict | None = None
    availability: Availability
    provenance: Provenance | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def provenance_required_when_available(self) -> Claim:
        if self.availability == Availability.AVAILABLE and self.provenance is None:
            raise ValueError("provenance is required when availability == AVAILABLE")
        if self.availability == Availability.AVAILABLE and self.value is None:
            raise ValueError("value is required when availability == AVAILABLE")
        return self


class Entity(BaseModel):
    """Core identity from the official registry — ground truth."""

    org_number: str
    legal_name: str
    brand_names: list[str] = Field(default_factory=list)
    status: str  # active | dissolved | bankrupt | winding_down | unknown
    registered_address: str | None = None
    legal_form: str | None = None  # AS, ASA, ENK, etc.
    industry_code: str | None = None
    industry_description: str | None = None
    founding_date: str | None = None
    employee_count: int | None = None
    parent_org_number: str | None = None
    website: str | None = None  # registry-declared hjemmeside
    latest_filed_accounts: str | None = None  # sisteInnsendteAarsregnskap


class CompanyProfile(BaseModel):
    """Complete company profile with claim-level evidence."""

    entity: Entity

    # Section 1: Legal identity and public brand
    official_site: Claim
    linkedin_url: Claim

    # Section 2: Financial data
    latest_filed_accounts: Claim

    # Section 3: Leadership and workplaces
    leadership: list[Claim] = Field(default_factory=list)
    locations: list[Claim] = Field(default_factory=list)

    # Section 4: Company profiles and presence
    headcount_band: Claim

    # Section 5: Hiring and activity
    hiring_signal: Claim
    dated_activity: list[Claim] = Field(default_factory=list)

    # Metadata
    profile_generated_at: datetime
    schema_version: str = "0.2"


class RefreshMetadata(BaseModel):
    """Tracks what changed since the previous run."""

    previous_snapshot_at: datetime | None = None
    material_changes: list[dict] = Field(default_factory=list)
    change_count: int = 0


class ResultEnvelope(BaseModel):
    """Terminal envelope — exactly one per input org number per batch."""

    org_number: str
    status: str  # "completed" | "error" | "skipped"
    profile: CompanyProfile | None = None
    refresh: RefreshMetadata | None = None
    error_detail: str | None = None
    batch_id: str
    processed_at: datetime

    @model_validator(mode="after")
    def profile_required_when_completed(self) -> ResultEnvelope:
        if self.status == "completed" and self.profile is None:
            raise ValueError("profile is required when status == completed")
        return self

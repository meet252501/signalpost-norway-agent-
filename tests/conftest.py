"""Shared pytest fixtures."""

from datetime import UTC, datetime

import pytest

from src.validate.schema import (
    Availability,
    Claim,
    CompanyProfile,
    Entity,
    Provenance,
)


@pytest.fixture
def sample_provenance() -> Provenance:
    return Provenance(
        source_url="https://example.no/about",
        retrieved_at=datetime.now(UTC),
        reporting_period="FY2025",
    )


@pytest.fixture
def found_claim(sample_provenance: Provenance) -> Claim:
    return Claim(
        value="https://example.no",
        availability=Availability.AVAILABLE,
        provenance=sample_provenance,
    )


@pytest.fixture
def missing_claim() -> Claim:
    return Claim(availability=Availability.NOT_AVAILABLE)


@pytest.fixture
def sample_profile(found_claim: Claim, missing_claim: Claim) -> CompanyProfile:
    entity = Entity(
        org_number="987654321",
        legal_name="Example AS",
        brand_names=["Example"],
        status="active",
        registered_address="Oslo, Norway",
    )
    return CompanyProfile(
        entity=entity,
        official_site=found_claim,
        linkedin_url=missing_claim,
        headcount_band=missing_claim,
        hiring_signal=missing_claim,
        latest_filed_accounts=missing_claim,
        profile_generated_at=datetime.now(UTC),
    )

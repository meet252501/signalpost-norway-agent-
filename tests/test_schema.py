"""Tests for the output-contract Pydantic models."""

import pytest
from pydantic import ValidationError

from src.validate.schema import Availability, Claim


def test_found_claim_requires_provenance():
    with pytest.raises(ValidationError):
        Claim(value="x", availability=Availability.AVAILABLE, provenance=None)


def test_found_claim_requires_value():
    with pytest.raises(ValidationError):
        Claim(value=None, availability=Availability.AVAILABLE, provenance=None)


def test_missing_claim_needs_no_provenance():
    claim = Claim(availability=Availability.NOT_AVAILABLE)
    assert claim.value is None
    assert claim.provenance is None


def test_sample_profile_is_valid(sample_profile):
    assert sample_profile.entity.org_number == "987654321"
    assert sample_profile.official_site.availability == Availability.AVAILABLE

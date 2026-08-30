"""
Tests for src/resolve/registry.py parsing logic. Deliberately test
parse_registry_record() directly against static fixtures — never call
fetch_registry_record() (real network) from automated tests.
"""

import json
from pathlib import Path

from src.resolve.registry import (
    parse_registry_record,
    registry_employee_count,
    registry_website,
)

ACTIVE = json.loads(Path("tests/golden/registry_sample_response.json").read_text(encoding="utf-8"))
DISSOLVED = json.loads(
    Path("tests/golden/registry_sample_response_dissolved.json").read_text(encoding="utf-8")
)
BANKRUPT = json.loads(
    Path("tests/golden/registry_sample_response_bankrupt.json").read_text(encoding="utf-8")
)


def test_parses_active_company():
    entity = parse_registry_record("987654321", ACTIVE)
    assert entity.org_number == "987654321"
    assert entity.legal_name == "Eksempel AS"
    assert entity.status == "active"
    assert entity.registered_address is not None
    assert "OSLO" in entity.registered_address


def test_parses_dissolved_company():
    entity = parse_registry_record("912345678", DISSOLVED)
    assert entity.status == "dissolved"


def test_parses_bankrupt_company():
    entity = parse_registry_record("998877665", BANKRUPT)
    assert entity.status == "bankrupt"


def test_registry_website_present():
    assert registry_website(ACTIVE) == "eksempel.no"


def test_registry_website_absent_returns_none():
    assert registry_website(DISSOLVED) is None


def test_registry_employee_count_present():
    assert registry_employee_count(ACTIVE) == 12


def test_registry_employee_count_absent_returns_none():
    assert registry_employee_count(DISSOLVED) is None

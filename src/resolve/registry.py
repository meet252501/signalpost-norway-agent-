"""
Entity resolution against Brønnøysundregisteret's Enhetsregisteret API.

See docs/algorithms/registry_api.md for the full endpoint/field notes
and the important caveat: the exact live API shape must be confirmed
with network access before this is trusted in production. The parsing
logic below is written against docs/algorithms/registry_api.md's
documented shape and is unit-tested against the synthetic fixtures in
tests/golden/ — it has NOT been run against the real live API from
this sandbox (no network access here).
"""

from __future__ import annotations

from src.budget import BatchBudget
from src.validate.schema import Entity

REGISTRY_BASE_URL = "https://data.brreg.no/enhetsregisteret/api/enheter"


def fetch_registry_record(
    org_number: str, timeout_s: float = 10.0, budget: BatchBudget | None = None
) -> dict | None:
    """
    Fetch the raw registry record for one org number.
    """
    import requests

    if budget:
        budget.check_and_spend(url=f"{REGISTRY_BASE_URL}/{org_number}")

    try:
        resp = requests.get(f"{REGISTRY_BASE_URL}/{org_number}", timeout=timeout_s)
        if resp.status_code != 200:
            return None
        return resp.json()
    except requests.RequestException:
        return None


def _format_address(addr: dict | None) -> str | None:
    if not addr:
        return None
    parts = list(addr.get("adresse", []))
    poststed = addr.get("poststed")
    postnummer = addr.get("postnummer")
    if postnummer and poststed:
        parts.append(f"{postnummer} {poststed}")
    elif poststed:
        parts.append(poststed)
    return ", ".join(p for p in parts if p) or None


def parse_registry_record(org_number: str, data: dict) -> Entity:
    """
    Parse the live API data into our Entity schema.
    """
    if data.get("slettedato"):
        status = "dissolved"
    elif data.get("konkurs"):
        status = "bankrupt"
    elif data.get("underAvvikling") or data.get("underTvangsavviklingEllerTvangsopplosning"):
        status = "winding_down"
    else:
        status = "active"

    org_form = data.get("organisasjonsform", {}).get("kode")
    industry_code = data.get("naeringskode1", {}).get("kode")
    industry_desc = data.get("naeringskode1", {}).get("beskrivelse")

    return Entity(
        org_number=org_number,
        legal_name=data.get("navn", ""),
        status=status,
        registered_address=_format_address(data.get("forretningsadresse")),
        legal_form=org_form,
        industry_code=industry_code,
        industry_description=industry_desc,
        founding_date=data.get("stiftelsesdato"),
        employee_count=data.get("antallAnsatte"),
        parent_org_number=data.get("overordnetEnhet"),
        website=data.get("hjemmeside"),
        latest_filed_accounts=data.get("sisteInnsendteAarsregnskap"),
    )


def resolve_entity(org_number: str, budget: BatchBudget | None = None) -> Entity:
    """
    Full resolution: fetch the live registry record and parse it. On
    fetch failure, returns a minimal Entity with status="unknown" so
    the pipeline can continue.
    """
    data = fetch_registry_record(org_number, budget=budget)
    if data is None:
        return Entity(org_number=org_number, legal_name="", status="unknown")
    return parse_registry_record(org_number, data)


def registry_website(data: dict) -> str | None:
    """
    Returns the registry-declared website if present and non-empty,
    else None. This is the tier-1 official-site candidate per
    docs/algorithms/resolve_algorithm.md — highest confidence because
    it's self-reported to a government registry, not discovered.
    """
    site = data.get("hjemmeside")
    return site if site else None


def registry_employee_count(data: dict) -> int | None:
    """
    Returns the registry-reported employee count (antallAnsatte), when
    present. Confirmed as a real field in the live API docs
    (docs/algorithms/registry_api.md) — this should feed
    CompanyProfile.headcount_band directly as a FOUND claim with the
    registry as provenance, rather than inferring headcount from
    LinkedIn text as originally planned.
    """
    count = data.get("antallAnsatte")
    return count if isinstance(count, int) else None

"""
Main pipeline execution.
Given an org_number, runs the entire resolution, crawl, extraction, and validation pipeline.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

from src.budget import BatchBudget
from src.crawl.fetcher import fetch_url
from src.crawl.playwright_fetcher import fetch_with_playwright
from src.crawl.sitemap import get_candidate_routes
from src.extract.structured import extract_structured_data, find_social_links
from src.extract.text import extract_main_text
from src.match.normalize import match_decision, name_similarity
from src.resolve.registry import resolve_entity
from src.validate.schema import (
    Availability,
    Claim,
    CompanyProfile,
    Entity,
    Provenance,
    ResultEnvelope,
)

logger = logging.getLogger(__name__)


def build_missing_claim() -> Claim:
    return Claim(availability=Availability.NOT_AVAILABLE)


def verify_name_match(extracted_name: str, entity: Entity) -> bool:
    """Verifies if an extracted name matches the registry legal name."""
    score = name_similarity(extracted_name, entity.legal_name)
    decision = match_decision(
        score, has_corroborating_signal=True
    )  # Assuming URL was reached via registry
    return decision == "accept"


def process_company(
    org_number: str, budget: BatchBudget, batch_id: str = "batch_1"
) -> ResultEnvelope:
    error_detail = None
    profile = None

    try:
        # 1. Resolve against registry
        entity = resolve_entity(org_number, budget=budget)

        # Initialize default claims
        official_site = build_missing_claim()
        linkedin_url = build_missing_claim()
        headcount_band = build_missing_claim()
        latest_filed_accounts = build_missing_claim()
        hiring_signal = build_missing_claim()

        # 2. Extract from registry directly
        if entity.website:
            official_site = Claim(
                value=entity.website
                if entity.website.startswith("http")
                else f"https://{entity.website}",
                availability=Availability.AVAILABLE,
                provenance=Provenance(
                    source_url="https://data.brreg.no",
                    retrieved_at=datetime.now(UTC),
                    extraction_method="registry_hjemmeside",
                ),
            )
        else:
            # Fallback: Search for the website
            from src.crawl.search import search_company_website
            candidate_url = search_company_website(entity.legal_name, budget)
            if candidate_url:
                official_site = Claim(
                    value=candidate_url,
                    availability=Availability.AVAILABLE,
                    provenance=Provenance(
                        source_url="https://duckduckgo.com",
                        retrieved_at=datetime.now(UTC),
                        extraction_method="search_engine_fallback",
                    ),
                )

        if entity.employee_count is not None:
            # Simple banding example
            if entity.employee_count == 0:
                band = "0"
            elif entity.employee_count <= 10:
                band = "1-10"
            elif entity.employee_count <= 50:
                band = "11-50"
            elif entity.employee_count <= 200:
                band = "51-200"
            elif entity.employee_count <= 500:
                band = "201-500"
            elif entity.employee_count <= 1000:
                band = "501-1000"
            elif entity.employee_count <= 5000:
                band = "1001-5000"
            elif entity.employee_count <= 10000:
                band = "5001-10000"
            else:
                band = "10001+"

            headcount_band = Claim(
                value=band,
                availability=Availability.AVAILABLE,
                provenance=Provenance(
                    source_url="https://data.brreg.no",
                    retrieved_at=datetime.now(UTC),
                    extraction_method="registry_antallAnsatte",
                ),
            )

        if entity.latest_filed_accounts:
            latest_filed_accounts = Claim(
                value=entity.latest_filed_accounts,
                availability=Availability.AVAILABLE,
                provenance=Provenance(
                    source_url="https://data.brreg.no",
                    retrieved_at=datetime.now(UTC),
                    extraction_method="registry_sisteInnsendteAarsregnskap",
                ),
            )

        # 3. Crawl official site if present
        if official_site.availability == Availability.AVAILABLE:
            url = str(official_site.value)

            # Fetch HTML (Try Static, Fallback to Playwright if empty/error)
            html = None
            resp = fetch_url(url, budget)
            if resp and resp.status_code == 200 and len(resp.text) > 1000:
                html = resp.text
            else:
                html = fetch_with_playwright(url, budget)

            if html:
                # If we used the search fallback, verify the title
                if official_site.provenance.extraction_method == "search_engine_fallback":
                    from src.match.normalize import match_decision, name_similarity
                    title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
                    title = title_match.group(1) if title_match else ""
                    
                    similarity = name_similarity(entity.legal_name, title)
                    if match_decision(similarity, has_corroborating_signal=False) != "accept":
                        # Failed verification, skip extracting from this site
                        logger.info(
                            f"Rejected search fallback for {entity.legal_name}: "
                            f"title '{title}' did not match."
                        )
                        official_site = build_missing_claim()
                        html = None # Skip further extraction
                
            if html:
                # Extract structured
                structured = extract_structured_data(html, url)

                # Check for linkedin in JSON-LD first
                for item in structured.get("json-ld", []):
                    same_as = item.get("sameAs", [])
                    if isinstance(same_as, str):
                        same_as = [same_as]
                    for link in same_as:
                        if "linkedin.com/company" in link.lower():
                            linkedin_url = Claim(
                                value=link,
                                availability=Availability.AVAILABLE,
                                provenance=Provenance(
                                    source_url=url,
                                    retrieved_at=datetime.now(UTC),
                                    extraction_method="json-ld_sameAs",
                                ),
                            )
                            break
                    if linkedin_url.availability == Availability.AVAILABLE:
                        break

                # Find social links fallback
                if linkedin_url.availability == Availability.NOT_AVAILABLE:
                    social_links = find_social_links(html)
                    for link in social_links:
                        if "linkedin.com/company" in link:
                            linkedin_url = Claim(
                                value=link,
                                availability=Availability.AVAILABLE,
                                provenance=Provenance(
                                    source_url=url,
                                    retrieved_at=datetime.now(UTC),
                                    extraction_method="html_href_match",
                                ),
                            )
                            break

                # Extract Hiring Signal via Sitemap routes
                routes = get_candidate_routes(url, budget)
                if routes["careers"]:
                    career_url = routes["careers"][0]  # Pick first career page
                    career_html = None
                    c_resp = fetch_url(career_url, budget)
                    if c_resp and c_resp.status_code == 200:
                        career_html = c_resp.text
                    else:
                        career_html = fetch_with_playwright(career_url, budget)

                    if career_html:
                        career_text = extract_main_text(career_html)
                        if career_text:
                            # Basic NLP pattern match
                            hiring_keywords = re.compile(
                                r"(ledige stillinger|apply now|we are hiring|"
                                r"join our team|open positions)",
                                re.IGNORECASE,
                            )
                            if hiring_keywords.search(career_text):
                                hiring_signal = Claim(
                                    value=True,
                                    availability=Availability.AVAILABLE,
                                    provenance=Provenance(
                                        source_url=career_url,
                                        retrieved_at=datetime.now(UTC),
                                        extraction_method="trafilatura_keyword_match",
                                    ),
                                )

        profile = CompanyProfile(
            entity=entity,
            official_site=official_site,
            linkedin_url=linkedin_url,
            latest_filed_accounts=latest_filed_accounts,
            headcount_band=headcount_band,
            hiring_signal=hiring_signal,
            profile_generated_at=datetime.now(UTC),
        )
        status = "completed"

    except Exception as e:
        logger.exception(f"Error processing {org_number}: {e}")
        error_detail = str(e)
        status = "error"

    return ResultEnvelope(
        org_number=org_number,
        status=status,
        profile=profile,
        error_detail=error_detail,
        batch_id=batch_id,
        processed_at=datetime.now(UTC),
    )

"""
Sitemap discovery and route selection.
Finds candidate pages for specific types of data (e.g. jobs, about, team).
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from src.budget import BatchBudget
from src.crawl.fetcher import USER_AGENT, _get_robots_parser

logger = logging.getLogger(__name__)


def find_sitemap_urls(domain_url: str, budget: BatchBudget) -> list[str]:
    """
    Attempts to find sitemap URLs via robots.txt or default locations.
    """
    sitemaps = []
    rp = _get_robots_parser(domain_url, budget)
    if rp.site_maps():
        sitemaps.extend(rp.site_maps())

    # Fallback to common locations if none found
    if not sitemaps:
        parsed = urlparse(domain_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        sitemaps.append(urljoin(base, "/sitemap.xml"))
        sitemaps.append(urljoin(base, "/sitemap_index.xml"))

    return sitemaps


def get_candidate_routes(domain_url: str, budget: BatchBudget) -> dict[str, list[str]]:
    """
    Finds routes categorized by purpose (careers, about).
    """
    sitemaps = find_sitemap_urls(domain_url, budget)
    routes = {"careers": set(), "about": set()}

    # Heuristics for URLs
    career_patterns = re.compile(
        r"(/careers?|/jobs?|/stillinger|/ledige-stillinger|/karriere)", re.IGNORECASE
    )
    about_patterns = re.compile(r"(/about|/om-oss|/team|/ledelse|/om-selskapet)", re.IGNORECASE)

    # For budget reasons, we'll only fetch the first valid sitemap.
    for sm_url in sitemaps:
        if not budget.can_spend_request():
            break

        try:
            budget.check_and_spend(sm_url)
            resp = requests.get(sm_url, headers={"User-Agent": USER_AGENT}, timeout=5.0)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, "xml")
                # Look for <loc>
                for loc in soup.find_all("loc"):
                    url = loc.text
                    if career_patterns.search(url):
                        routes["careers"].add(url)
                    if about_patterns.search(url):
                        routes["about"].add(url)
                break  # Only process one main sitemap to save budget
        except Exception as e:
            logger.debug(f"Failed to fetch sitemap {sm_url}: {e}")

    return {k: list(v) for k, v in routes.items()}

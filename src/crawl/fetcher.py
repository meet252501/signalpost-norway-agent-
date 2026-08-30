"""
Crawl fetcher with robust timeout, retries, and budget tracking.
Uses requests for static fetching.
Respects robots.txt.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.budget import BatchBudget

logger = logging.getLogger(__name__)

USER_AGENT = "SignalpostNorway/1.0 (Company Research; +https://signalpost.ai/bot)"

_robot_parsers: dict[str, RobotFileParser] = {}


def _get_robots_parser(domain_url: str, budget: BatchBudget) -> RobotFileParser:
    parsed = urlparse(domain_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    if robots_url in _robot_parsers:
        return _robot_parsers[robots_url]

    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        # We must spend budget to read robots.txt
        budget.check_and_spend(robots_url)
        # We manually fetch so we can set the User-Agent and timeout
        resp = requests.get(robots_url, headers={"User-Agent": USER_AGENT}, timeout=5.0)
        if resp.status_code == 200:
            rp.parse(resp.text.splitlines())
    except Exception as e:
        logger.debug(f"Failed to fetch {robots_url}: {e}")
        # Default allow if we can't fetch it, per standard behavior

    _robot_parsers[robots_url] = rp
    return rp


def fetch_url(url: str, budget: BatchBudget, timeout: float = 15.0) -> requests.Response | None:
    """
    Fetch a URL statically, obeying robots.txt and budget.
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None

    # 1. Robots check
    rp = _get_robots_parser(url, budget)
    if not rp.can_fetch(USER_AGENT, url):
        logger.warning(f"robots.txt blocked fetch for {url}")
        return None

    # 2. Spend budget
    budget.check_and_spend(url)

    # 3. Fetch with retries
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
    )
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))

    try:
        resp = session.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=timeout, allow_redirects=True
        )
        return resp
    except Exception as e:
        logger.debug(f"Fetch failed for {url}: {e}")
        return None

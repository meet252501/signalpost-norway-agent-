"""
Playwright-based fetcher for SPAs and JavaScript-heavy sites.
Used ONLY as a fallback if the static fetcher fails or returns empty/skeleton HTML.
"""

from __future__ import annotations

import logging

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from src.budget import BatchBudget

logger = logging.getLogger(__name__)


def fetch_with_playwright(url: str, budget: BatchBudget, timeout_ms: int = 15000) -> str | None:
    """
    Fetch a URL using Playwright. Checks budget before fetching.
    Returns the full HTML string or None on failure.
    """
    if not budget.can_spend_request():
        logger.warning(f"Budget exhausted before Playwright fetch for {url}")
        return None

    budget.check_and_spend(url)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent="SignalpostNorway/1.0 (Company Research; +https://signalpost.ai/bot)"
            )
            page.set_default_timeout(timeout_ms)

            try:
                # Wait until network is mostly idle to ensure JS renders
                page.goto(url, wait_until="networkidle")
            except PlaywrightTimeoutError:
                # If networkidle times out, just take whatever is there
                logger.debug(
                    f"Playwright networkidle timeout for {url}, falling back to loaded state."
                )
                pass

            html = page.content()
            browser.close()
            return html
    except Exception as e:
        logger.debug(f"Playwright fetch failed for {url}: {e}")
        return None

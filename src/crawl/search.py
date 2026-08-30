"""
Search engine fallback for discovering company websites.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import quote_plus, unquote

from src.budget import BatchBudget
from src.crawl.fetcher import fetch_url

logger = logging.getLogger(__name__)

FORBIDDEN_DOMAINS = [
    "proff.no",
    "purehelp.no",
    "gulesider.no",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "1881.no",
    "regnskapstall.no",
    "io.no",
    "nordicnet.no",
    "finn.no",
    "startsiden.no",
    "brreg.no",
]

def search_company_website(legal_name: str, budget: BatchBudget) -> str | None:
    """
    Perform a lightweight DuckDuckGo HTML search for the company.
    Returns the top candidate URL, filtering out aggregator domains.
    """
    # Need to be very precise to avoid grabbing random sites
    query = quote_plus(f'"{legal_name}" norge')
    url = f"https://html.duckduckgo.com/html/?q={query}"
    
    # DuckDuckGo will block bot user-agents, so we use a standard one for search
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # We must spend budget for the search
    budget.check_and_spend(url)
    
    import requests
    try:
        resp = requests.get(url, headers=headers, timeout=10.0)
        if resp.status_code != 200:
            return None
        html = resp.text
    except Exception as e:
        logger.debug(f"Search failed for {legal_name}: {e}")
        return None
    
    matches = re.finditer(r'uddg=([^&"\']+)', html)
    for match in matches:
        link = unquote(match.group(1))
            
        if not link.startswith("http"):
            continue
            
        # Check against forbidden domains
        forbidden = False
        for fd in FORBIDDEN_DOMAINS:
            if fd in link.lower():
                forbidden = True
                break
                
        if not forbidden:
            logger.info(f"Search found candidate website for {legal_name}: {link}")
            return link
            
    return None

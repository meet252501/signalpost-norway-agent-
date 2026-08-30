"""
Structured data extraction from HTML.
Extracts JSON-LD, Microdata, OpenGraph using extruct.
"""

from __future__ import annotations

from typing import Any

import extruct
from bs4 import BeautifulSoup


def extract_structured_data(html: str, base_url: str) -> dict[str, Any]:
    """
    Extracts all structured data from the given HTML.
    Focuses on JSON-LD, microdata, and opengraph.
    """
    try:
        data = extruct.extract(
            html, base_url=base_url, syntaxes=["json-ld", "microdata", "opengraph"]
        )
        return data
    except Exception:
        return {"json-ld": [], "microdata": [], "opengraph": []}


def find_social_links(html: str) -> list[str]:
    """
    Fallback social link finding (from hrefs containing known social domains)
    if not explicitly present in structured data.
    """
    soup = BeautifulSoup(html, "html.parser")
    social_domains = [
        "linkedin.com/company/",
        "facebook.com/",
        "twitter.com/",
        "x.com/",
        "instagram.com/",
    ]
    found = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        for dom in social_domains:
            if dom in href:
                found.add(a["href"])
    return list(found)

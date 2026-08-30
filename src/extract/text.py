"""
Text extraction from HTML using Trafilatura.
"""

from __future__ import annotations

import trafilatura


def extract_main_text(html: str) -> str | None:
    """
    Extracts the main readable text from an HTML document.
    """
    # include_comments=False, include_tables=True, include_links=False
    text = trafilatura.extract(html, include_links=True)
    return text

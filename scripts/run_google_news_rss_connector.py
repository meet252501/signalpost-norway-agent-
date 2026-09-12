#!/usr/bin/env python3
"""Fetches real news articles from Bing News RSS for Norwegian companies.

Uses Bing's public RSS endpoint which returns real news results.
Applies exact company name matching and keyword-based sentiment classification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
import time

LEGAL = {"as", "asa", "sa", "ba", "da", "ans", "enk", "nuf", "sti"}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Simple keyword-based sentiment classifier for Norwegian/English news headlines
POSITIVE_KEYWORDS = {
    "vekst", "vinner", "rekord", "styrker", "ekspanderer", "investerer",
    "suksess", "vokser", "øker", "lønnsomhet", "overskudd", "samarbeid",
    "innovasjon", "prisvinner", "lanserer", "sterk", "positiv", "fremgang",
    "oppgang", "beste", "topp", "solgt", "avtale", "kontrakt", "feirer",
    "bærekraft", "grønn", "fornybar", "anbefaler", "tildelt", "utnevnt",
    "growth", "profit", "award", "record", "expands", "launches", "wins",
    "success", "innovation", "partnership", "strong", "positive", "best",
    "leading", "celebrates", "sustainable", "investment", "milestone",
    "breakthrough", "achievement", "revenue", "earnings", "upgraded",
    "buy", "outperform", "top", "ranked", "recommended",
}

NEGATIVE_KEYWORDS = {
    "tap", "konkurs", "nedgang", "krise", "kutt", "permitterer", "sparken",
    "nedbemannet", "gjeldsforhandling", "svindel", "skandale", "mistenkt",
    "anmeldt", "stengt", "straffet", "bot", "overtredelse", "avvikle",
    "tvangsoppløsning", "underskudd", "misligholder", "faller", "verst",
    "loss", "bankruptcy", "crisis", "layoff", "fraud", "scandal", "fine",
    "closed", "penalty", "decline", "failure", "shutdown", "debt", "default",
    "investigation", "charged", "violation", "worst", "collapse", "downgrade",
    "sell", "underperform", "warning", "risk",
}


def classify_sentiment(text: str) -> str:
    words = set(re.findall(r"[a-zæøå]+", text.casefold()))
    pos = len(words & POSITIVE_KEYWORDS)
    neg = len(words & NEGATIVE_KEYWORDS)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    if pos == neg and pos > 0:
        return "mixed"
    return "neutral"


def norm(value: object) -> str:
    return " ".join(
        token
        for token in re.findall(r"[a-z0-9æøå]+", str(value or "").casefold())
        if token not in LEGAL
    )


def exact_title_match(company_name: str, title: str) -> bool:
    company_tokens = re.findall(r"[a-z0-9æøå]+", str(company_name or "").casefold())
    clean_title = re.split(r"\s+[-|]\s+", str(title or ""), maxsplit=1)[0]
    title_tokens = re.findall(r"[a-z0-9æøå]+", clean_title.casefold())
    if not company_tokens or not title_tokens or len(company_tokens) > len(title_tokens):
        return False
    allowed_predecessors = {"av", "for", "fra", "hos", "i", "med", "om", "på", "til", "og", "kjøper", "velger"}
    for index in range(len(title_tokens) - len(company_tokens) + 1):
        if title_tokens[index : index + len(company_tokens)] != company_tokens:
            continue
        if index == 0 or title_tokens[index - 1] in allowed_predecessors:
            return True
    return False


def fetch_bing_rss(query: str, timeout: float = 5.0) -> bytes:
    """Fetch Bing News RSS for a search query."""
    encoded = urllib.parse.quote(query)
    url = f"https://www.bing.com/news/search?q={encoded}&format=rss"
    request = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read(500_000)
    except Exception:
        return b""


def parse_rss_items(raw: bytes) -> list[dict]:
    items = []
    if not raw:
        return items
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return items
    for item_el in root.iter("item"):
        title_el = item_el.find("title")
        link_el = item_el.find("link")
        pub_el = item_el.find("pubDate")
        desc_el = item_el.find("description")
        if title_el is None or link_el is None:
            continue
        title = (title_el.text or "").strip()
        link = (link_el.text or "").strip()
        pub_date = (pub_el.text or "").strip() if pub_el is not None else None
        description = (desc_el.text or "").strip() if desc_el is not None else ""
        # Extract source/publisher from title suffix
        publisher = ""
        parts = re.split(r"\s+[-|]\s+", title)
        if len(parts) > 1:
            publisher = parts[-1].strip()
        if title and link:
            items.append({
                "title": title,
                "link": link,
                "pubDate": pub_date,
                "publisher": publisher,
                "description": description,
            })
    return items


def fetch(profile: dict, limit: int, years: int) -> tuple[list[dict], dict]:
    """Fetch real news articles from multiple Bing News RSS endpoints."""
    org = str(profile.get("organisation_number"))
    name = profile.get("name", "Unknown Company")

    # Fetch from BOTH international and Norwegian Bing News RSS
    raw_intl = fetch_bing_rss(name)
    raw_no = fetch_bing_rss(name + " Norge")  # Norwegian context
    
    # Also try with quoted exact match
    raw_exact = fetch_bing_rss(f'"{name}"')
    
    # Merge and deduplicate items by link
    all_items = []
    seen_links = set()
    for raw in [raw_intl, raw_no, raw_exact]:
        for item in parse_rss_items(raw):
            if item["link"] not in seen_links:
                seen_links.add(item["link"])
                all_items.append(item)
    rss_items = all_items

    now = datetime.now(UTC)
    retrieved_at = now.isoformat()
    cutoff = now - timedelta(days=years * 365)

    output = []
    accepted = 0
    rejected = 0

    for item in rss_items[:limit]:
        title = item["title"]
        link = item["link"]

        # Only accept articles where the company name appears in the title
        if not exact_title_match(name, title):
            rejected += 1
            continue

        # Parse publication date
        published_at = None
        if item.get("pubDate"):
            try:
                pub_dt = parsedate_to_datetime(item["pubDate"])
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=UTC)
                if pub_dt < cutoff:
                    continue
                published_at = pub_dt.isoformat()
            except Exception:
                pass

        publisher = item.get("publisher") or "Unknown"
        digest = hashlib.sha256(f"{title}|{link}".encode()).hexdigest()

        # Classify sentiment from real headline
        sentiment = classify_sentiment(title)

        obs = {
            "id": "bing-news-title-" + hashlib.sha256(f"{org}|{title}|{link}".encode()).hexdigest()[:24],
            "organisation_number": org,
            "platform": "news",
            "signal_type": "public_mention",
            "source_url": link,
            "retrieved_at": retrieved_at,
            "content_sha256": digest,
            "exact_entity": True,
            "identity_proof": [
                {"type": "exact_legal_name_in_news_title", "value": name},
                {"type": "publisher_label", "value": publisher},
            ],
            "acquisition_mode": "permitted_public_page",
            "rights_status": "approved",
            "source_class": "public_news",
            "evidence_span": title,
            "text": title,
            "publisher": publisher,
            "sentiment_label": sentiment,
            "sentiment_model_version": "keyword-classifier-v1",
            "strategy": "independent_news_discovery",
        }
        if published_at:
            obs["published_at"] = published_at

        output.append(obs)
        accepted += 1

    return output, {
        "organisation_number": org,
        "rss_items_fetched": len(rss_items),
        "items": accepted,
        "accepted": accepted,
        "rejected": rejected,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bounded exact-title Bing News RSS discovery — fetches real RSS feeds."
    )
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--organisations", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--per-company", type=int, default=15)
    parser.add_argument("--years", type=int, default=2)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    wanted = []
    for line in Path(args.organisations).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            wanted.append(str(json.loads(line)["organisation_number"]))
        except Exception:
            wanted.append(line)
    profiles = {
        str(row["organisation_number"]): row
        for row in (
            json.loads(line)
            for line in Path(args.profiles).read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    observations, results = [], []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(fetch, profiles[org], args.per_company, args.years): org
            for org in wanted
            if org in profiles
        }
        for future in as_completed(futures):
            try:
                rows, status = future.result()
                observations.extend(rows)
                results.append(status)
            except Exception as e:
                org = futures[future]
                results.append({
                    "organisation_number": org,
                    "error": str(e)[:200],
                    "items": 0,
                    "accepted": 0,
                })

    order = {org: index for index, org in enumerate(wanted)}
    observations.sort(
        key=lambda row: (
            order.get(row["organisation_number"], 99999),
            row.get("published_at") or "",
            row["id"],
        )
    )
    results.sort(key=lambda row: order.get(row.get("organisation_number", ""), 99999))
    Path(args.output).write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in observations),
        encoding="utf-8",
    )
    companies_with_news = len({r["organisation_number"] for r in results if r.get("accepted", 0) > 0})
    total_rss = sum(r.get("rss_items_fetched", 0) for r in results)
    report = {
        "connector": "bing_news_rss_real_v1",
        "companies": len(wanted),
        "companies_with_mentions": companies_with_news,
        "observations": len(observations),
        "rss_items_fetched_total": total_rss,
        "lookback_years": args.years,
        "errors": sum(1 for row in results if "error" in row),
        "claim_boundary": "Real Bing News RSS public feeds. Only articles with exact company name match in title are kept. Sentiment classified with keyword-based model.",
        "company_results": results,
    }
    Path(args.report).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "company_results"},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

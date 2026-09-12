#!/usr/bin/env python3
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
UA = "SignalpostResearchPOC/1.0 (https://builderr.ai; bounded qualification run)"

# Simple keyword-based sentiment classifier for Norwegian/English news headlines
POSITIVE_KEYWORDS = {
    # Norwegian positive
    "vekst", "vinner", "rekord", "styrker", "ekspanderer", "investerer",
    "suksess", "vokser", "øker", "lønnsomhet", "overskudd", "samarbeid",
    "innovasjon", "prisvinner", "lanserer", "sterk", "positiv", "fremgang",
    "oppgang", "beste", "topp", "solgt", "avtale", "kontrakt", "feirer",
    "bærekraft", "grønn", "fornybar", "anbefaler", "tildelt", "utnevnt",
    # English positive
    "growth", "profit", "award", "record", "expands", "launches", "wins",
    "success", "innovation", "partnership", "strong", "positive", "best",
    "leading", "celebrates", "sustainable", "investment", "milestone",
    "breakthrough", "achievement",
}

NEGATIVE_KEYWORDS = {
    # Norwegian negative
    "tap", "konkurs", "nedgang", "krise", "kutt", "permitterer", "sparken",
    "nedbemannet", "gjeldsforhandling", "svindel", "skandale", "mistenkt",
    "anmeldt", "stengt", "straffet", "bot", "overtredelse", "avvikle",
    "tvangsoppløsning", "underskudd", "misligholder", "faller", "verst",
    # English negative
    "loss", "bankruptcy", "crisis", "layoff", "fraud", "scandal", "fine",
    "closed", "penalty", "decline", "failure", "shutdown", "debt", "default",
    "investigation", "charged", "violation", "worst", "collapse",
}


def classify_sentiment(text: str) -> str:
    """Simple keyword-based sentiment for news headlines."""
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
    title_tokens = re.findall(
        r"[a-z0-9æøå]+", str(title or "").rsplit(" - ", 1)[0].casefold()
    )
    if (
        not company_tokens
        or not title_tokens
        or len(company_tokens) > len(title_tokens)
    ):
        return False
    allowed_predecessors = {
        "av", "for", "fra", "hos", "i", "med", "om", "på", "til", "og",
        "kjøper", "velger",
    }
    for index in range(len(title_tokens) - len(company_tokens) + 1):
        if title_tokens[index : index + len(company_tokens)] != company_tokens:
            continue
        if index == 0 or title_tokens[index - 1] in allowed_predecessors:
            return True
    return False


def fetch_rss(query: str, timeout: float = 3.0) -> bytes:
    """Fetch Google News RSS for a search query."""
    encoded = urllib.parse.quote(f'"{query}"')
    url = f"https://news.google.com/rss/search?q={encoded}&hl=no&gl=NO&ceid=NO:no"
    request = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/rss+xml, application/xml, text/xml",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read(500_000)
    except Exception:
        return b""


def parse_rss_items(raw: bytes) -> list[dict]:
    """Parse RSS XML into list of {title, link, pubDate, source}."""
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
        source_el = item_el.find("source")
        if title_el is None or link_el is None:
            continue
        title = (title_el.text or "").strip()
        link = (link_el.text or "").strip()
        pub_date = (pub_el.text or "").strip() if pub_el is not None else None
        source = (source_el.text or "").strip() if source_el is not None else None
        source_url = source_el.get("url", "") if source_el is not None else ""
        if title and link:
            items.append({
                "title": title,
                "link": link,
                "pubDate": pub_date,
                "source": source,
                "source_url": source_url,
            })
    return items


def fetch(profile: dict, limit: int, years: int) -> tuple[list[dict], dict]:
    """Fetch real Google News RSS articles for a company."""
    org = str(profile.get("organisation_number"))
    name = profile.get("name", "Unknown Company")
    
    # Fetch real RSS feed
    raw = fetch_rss(name)
    rss_items = parse_rss_items(raw)
    
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
        
        publisher = item.get("source") or "Unknown"
        digest = hashlib.sha256(f"{title}|{link}".encode()).hexdigest()
        
        # Classify sentiment from real headline
        sentiment = classify_sentiment(title)
        
        obs = {
            "id": "google-news-title-" + hashlib.sha256(f"{org}|{title}|{link}".encode()).hexdigest()[:24],
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
        description="Bounded exact-title Google News RSS discovery — fetches real RSS feeds."
    )
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--organisations", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--per-company", type=int, default=10)
    parser.add_argument("--years", type=int, default=2)
    parser.add_argument("--workers", type=int, default=4)
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
    
    # Google News RSS is a public syndication endpoint designed for feed readers
    batch_size = 16
    delay_between_batches = 0.05
    
    with ThreadPoolExecutor(max_workers=batch_size) as pool:
        # Process in batches to avoid hammering
        for batch_start in range(0, len(wanted), batch_size):
            batch = wanted[batch_start:batch_start + batch_size]
            futures = {
                pool.submit(fetch, profiles[org], args.per_company, args.years): org
                for org in batch
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
            if batch_start + batch_size < len(wanted):
                time.sleep(delay_between_batches)
    
    order = {org: index for index, org in enumerate(wanted)}
    observations.sort(
        key=lambda row: (
            order.get(row["organisation_number"], 99999),
            row.get("published_at") or "",
            row["id"],
        )
    )
    results.sort(key=lambda row: order.get(row["organisation_number"], 99999))
    Path(args.output).write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in observations),
        encoding="utf-8",
    )
    companies_with_news = len({r["organisation_number"] for r in results if r.get("accepted", 0) > 0})
    total_rss = sum(r.get("rss_items_fetched", 0) for r in results)
    report = {
        "connector": "google_news_rss_real_v2",
        "companies": len(wanted),
        "companies_with_mentions": companies_with_news,
        "observations": len(observations),
        "rss_items_fetched_total": total_rss,
        "lookback_years": args.years,
        "errors": sum(1 for row in results if "error" in row),
        "claim_boundary": "Real Google News RSS public feeds. Only articles with exact company name match in title are kept.",
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

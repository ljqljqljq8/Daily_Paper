from __future__ import annotations

import re
from datetime import datetime, timezone

import feedparser
import requests

from daily_paper.config import Settings
from daily_paper.models import Paper
from daily_paper.utils import in_recent_days, now_utc, relevance_score

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ARXIV_ADVANCED_HINTS = [
    "ti:",
    "au:",
    "abs:",
    "co:",
    "jr:",
    "cat:",
    "rn:",
    "id:",
    "all:",
    "AND",
    "OR",
    "ANDNOT",
    "(",
]
ARXIV_CATEGORY_CODE_RE = re.compile(r"^[a-z\-]+\.[A-Za-z\-]+$")


def _build_arxiv_search_query(query: str) -> str:
    raw = query.strip()
    if ":" not in raw and "+" in raw and " " not in raw:
        parts = [part.strip() for part in raw.split("+") if part.strip()]
        if parts and all(ARXIV_CATEGORY_CODE_RE.match(part) for part in parts):
            return " OR ".join(f"cat:{part}" for part in parts)
    if "+" in raw:
        # arXiv examples commonly use '+' as URL-level separators for operators/space.
        # requests will encode literal '+' as %2B, so normalize to spaces first.
        raw = raw.replace("+", " ")
    if any(token in raw for token in ARXIV_ADVANCED_HINTS):
        return raw
    return f"all:{raw}"


def fetch_arxiv(query: str, settings: Settings) -> list[Paper]:
    params = {
        "search_query": _build_arxiv_search_query(query),
        "start": 0,
        "max_results": settings.max_results_per_query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    response = requests.get(
        ARXIV_API_URL,
        params=params,
        timeout=settings.request_timeout,
        headers={"User-Agent": settings.user_agent},
    )
    response.raise_for_status()
    feed = feedparser.parse(response.text)
    papers: list[Paper] = []
    for entry in feed.entries:
        published_raw = entry.get("published", "")
        published = now_utc()
        if published_raw:
            try:
                published = datetime.fromisoformat(published_raw.replace("Z", "+00:00")).astimezone(timezone.utc)
            except ValueError:
                pass

        if not in_recent_days(published, settings.days_back):
            continue

        title = " ".join((entry.get("title") or "").split())
        abstract = " ".join((entry.get("summary") or "").split())
        authors = [author.name for author in entry.get("authors", []) if getattr(author, "name", "")]
        doi = entry.get("arxiv_doi", "")
        links = entry.get("links", [])
        link = entry.get("link", "")
        for item in links:
            href = item.get("href", "")
            if href.startswith("http"):
                link = href
                break
        paper = Paper(
            source="arXiv",
            title=title,
            abstract=abstract,
            authors=authors,
            url=link,
            published=published,
            identifier=entry.get("id", ""),
            doi=doi,
            query=query,
            relevance=relevance_score(query, title, abstract),
        )
        papers.append(paper)
    return papers

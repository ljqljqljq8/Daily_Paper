from __future__ import annotations

import re

import requests

from daily_paper.config import Settings
from daily_paper.models import Paper
from daily_paper.utils import now_utc, parse_date_best_effort, relevance_score

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
YEAR_RE = re.compile(r"(19|20)\d{2}")


def fetch_scholar(query: str, settings: Settings) -> list[Paper]:
    if not settings.serpapi_api_key:
        return []

    params = {
        "engine": "google_scholar",
        "q": query,
        "api_key": settings.serpapi_api_key,
        "num": settings.max_results_per_query,
        "hl": "en",
        "scisbd": "1",
    }
    response = requests.get(
        SERPAPI_ENDPOINT,
        params=params,
        timeout=settings.request_timeout,
        headers={"User-Agent": settings.user_agent},
    )
    response.raise_for_status()
    data = response.json()
    organic = data.get("organic_results", [])
    papers: list[Paper] = []
    for row in organic:
        title = " ".join((row.get("title") or "").split())
        abstract = " ".join((row.get("snippet") or "").split())
        pub_info = row.get("publication_info", {}) or {}
        summary = pub_info.get("summary", "")
        authors = []
        if summary:
            authors = [part.strip() for part in summary.split("-")[0].split(",") if part.strip()]

        published = now_utc()
        m = YEAR_RE.search(summary or "")
        if m:
            published = parse_date_best_effort(m.group(0))

        resources = row.get("resources", []) or []
        link = row.get("link", "")
        if not link and resources:
            first = resources[0]
            if isinstance(first, dict):
                link = first.get("link", "")

        papers.append(
            Paper(
                source="Google Scholar",
                title=title,
                abstract=abstract,
                authors=authors,
                url=link,
                published=published,
                identifier=row.get("result_id", "") or link,
                doi="",
                query=query,
                relevance=relevance_score(query, title, abstract),
            )
        )
    return papers


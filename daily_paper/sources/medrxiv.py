from __future__ import annotations

import requests

from daily_paper.config import Settings
from daily_paper.models import Paper
from daily_paper.utils import parse_date_best_effort, relevance_score, utc_date_range

MEDRXIV_DETAILS_API = "https://api.biorxiv.org/details/medrxiv"


def _extract_category_expression(query: str) -> str:
    raw = query.strip()
    if raw.lower().startswith("category:"):
        return raw.split(":", 1)[1].strip()
    return ""


def fetch_medrxiv(query: str, settings: Settings) -> list[Paper]:
    start_date, end_date = utc_date_range(settings.days_back)
    cursor = 0
    papers: list[Paper] = []
    cap = max(settings.max_results_per_query * 5, 50)
    category_expression = _extract_category_expression(query)

    while len(papers) < settings.max_results_per_query and cursor < cap:
        url = f"{MEDRXIV_DETAILS_API}/{start_date}/{end_date}/{cursor}"
        response = requests.get(
            url,
            params={"category": category_expression} if category_expression else None,
            timeout=settings.request_timeout,
            headers={"User-Agent": settings.user_agent},
        )
        response.raise_for_status()
        data = response.json()
        collection = data.get("collection", [])
        if not collection:
            break

        for item in collection:
            title = " ".join((item.get("title") or "").split())
            abstract = " ".join((item.get("abstract") or "").split())
            authors_raw = item.get("authors", "")
            authors = [a.strip() for a in authors_raw.replace(";", ",").split(",") if a.strip()]
            doi = item.get("doi", "")
            version = item.get("version", "1")
            link = f"https://www.medrxiv.org/content/{doi}v{version}" if doi else item.get("url", "")
            published = parse_date_best_effort(item.get("date", ""))
            papers.append(
                Paper(
                    source="medRxiv",
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    url=link,
                    published=published,
                    identifier=doi or link,
                    doi=doi,
                    query=query,
                    relevance=relevance_score(query, title, abstract),
                )
            )
            if len(papers) >= settings.max_results_per_query:
                break

        cursor += len(collection)
        total = 0
        messages = data.get("messages") or []
        if messages and isinstance(messages, list):
            try:
                total = int(messages[0].get("total", 0))
            except Exception:
                total = 0
        if total and cursor >= total:
            break

    return papers

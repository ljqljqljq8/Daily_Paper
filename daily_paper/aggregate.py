from __future__ import annotations

from collections import defaultdict

from daily_paper.config import Settings
from daily_paper.models import Paper


def deduplicate_rank_limit(papers: list[Paper], settings: Settings) -> list[Paper]:
    best: dict[str, Paper] = {}
    for paper in papers:
        key = (paper.doi or "").lower().strip() or paper.normalized_title
        existing = best.get(key)
        if existing is None:
            best[key] = paper
            continue
        current_score = (paper.relevance, paper.published.timestamp())
        existing_score = (existing.relevance, existing.published.timestamp())
        if current_score > existing_score:
            best[key] = paper

    sorted_papers = sorted(
        best.values(),
        key=lambda p: (p.published, p.relevance, p.source.lower()),
        reverse=True,
    )
    return sorted_papers[: settings.max_total_results]


def group_by_source(papers: list[Paper]) -> dict[str, list[Paper]]:
    grouped: dict[str, list[Paper]] = defaultdict(list)
    for paper in papers:
        grouped[paper.source].append(paper)
    for source in grouped:
        grouped[source].sort(key=lambda p: (p.published, p.relevance), reverse=True)
    return dict(sorted(grouped.items(), key=lambda x: x[0].lower()))


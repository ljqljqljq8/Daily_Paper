from __future__ import annotations

import logging
from pathlib import Path

from daily_paper.aggregate import deduplicate_rank_limit, group_by_source
from daily_paper.config import Settings
from daily_paper.emailer import send_email
from daily_paper.models import Paper
from daily_paper.render import render_html, render_markdown
from daily_paper.sources import fetch_arxiv, fetch_medrxiv, fetch_pubmed, fetch_scholar
from daily_paper.utils import local_date_string

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
logger = logging.getLogger("daily-paper")

SOURCE_FETCHERS = {
    "arxiv": fetch_arxiv,
    "medrxiv": fetch_medrxiv,
    "pubmed": fetch_pubmed,
    "scholar": fetch_scholar,
}


def collect_papers(settings: Settings) -> list[Paper]:
    all_papers: list[Paper] = []
    for source_name in settings.enabled_sources:
        key = source_name.lower().strip()
        fetcher = SOURCE_FETCHERS.get(key)
        if fetcher is None:
            logger.warning("Skip unknown source: %s", source_name)
            continue
        if key == "scholar" and not settings.serpapi_api_key:
            logger.info("Skip Google Scholar because SERPAPI_API_KEY is not configured.")
            continue

        source_queries = settings.queries_for_source(key)
        if not source_queries:
            logger.info("Skip %s because no query is configured for this source.", source_name)
            continue

        for query in source_queries:
            try:
                papers = fetcher(query, settings)
                logger.info("%s -> query=%s fetched=%d", source_name, query, len(papers))
                all_papers.extend(papers)
            except Exception as exc:
                logger.exception("Fetch failed: source=%s query=%s error=%s", source_name, query, exc)
    return all_papers


def main() -> None:
    settings = Settings.from_env()
    date_str = local_date_string(settings.report_timezone)
    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_papers = collect_papers(settings)
    final_papers = deduplicate_rank_limit(raw_papers, settings)
    grouped = group_by_source(final_papers)

    markdown = render_markdown(date_str, settings.topic_queries, grouped)
    html = render_html(date_str, settings.topic_queries, grouped)

    md_path = output_dir / f"{date_str}.md"
    html_path = output_dir / f"{date_str}.html"
    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    logger.info("Saved reports: %s and %s", md_path, html_path)

    if not final_papers and not settings.send_empty_digest:
        logger.info("No papers found and SEND_EMPTY_DIGEST is false. Skip email.")
        return

    subject = f"[Daily Paper Digest] {date_str} ({len(final_papers)} papers)"
    if settings.dry_run:
        logger.info("DRY_RUN=true, skip email send.")
        return

    send_email(settings, subject=subject, html_body=html, text_body=markdown)
    logger.info("Email sent successfully to %s", ", ".join(settings.email_receivers))


if __name__ == "__main__":
    main()

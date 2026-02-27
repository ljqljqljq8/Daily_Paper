from __future__ import annotations

import logging
from pathlib import Path

from daily_paper.aggregate import deduplicate_rank_limit, group_by_source
from daily_paper.config import Settings
from daily_paper.emailer import send_email
from daily_paper.models import Paper
from daily_paper.render import render_html, render_markdown
from daily_paper.similarity import SimilarityEngine, apply_similarity_filter, build_seed_queries
from daily_paper.sources import fetch_arxiv, fetch_medrxiv, fetch_pubmed, fetch_scholar
from daily_paper.utils import local_date_string
from daily_paper.zotero import ZoteroRecord, fetch_zotero_records

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
logger = logging.getLogger("daily-paper")

SOURCE_FETCHERS = {
    "arxiv": fetch_arxiv,
    "medrxiv": fetch_medrxiv,
    "pubmed": fetch_pubmed,
    "scholar": fetch_scholar,
}


def _queries_for_source(settings: Settings, source: str, auto_queries: list[str], use_profile: bool) -> list[str]:
    manual_queries = settings.queries_for_source(source)
    if manual_queries:
        return manual_queries
    if source == "medrxiv" and use_profile:
        # medRxiv details API supports date/category crawl. Empty query means "crawl recent and rank by similarity".
        return [""]
    return auto_queries


def collect_papers(settings: Settings, auto_queries: list[str], use_profile: bool) -> tuple[list[Paper], list[str]]:
    all_papers: list[Paper] = []
    used_queries: list[str] = []
    for source_name in settings.enabled_sources:
        key = source_name.lower().strip()
        fetcher = SOURCE_FETCHERS.get(key)
        if fetcher is None:
            logger.warning("Skip unknown source: %s", source_name)
            continue
        if key == "scholar" and not settings.serpapi_api_key:
            logger.info("Skip Google Scholar because SERPAPI_API_KEY is not configured.")
            continue

        source_queries = _queries_for_source(settings, key, auto_queries, use_profile=use_profile)
        if not source_queries:
            logger.info("Skip %s because no query is configured for this source.", source_name)
            continue

        for query in source_queries:
            try:
                papers = fetcher(query, settings)
                query_for_log = query or "[zotero-profile-wide]"
                logger.info("%s -> query=%s fetched=%d", source_name, query_for_log, len(papers))
                if papers and not query:
                    for paper in papers:
                        paper.query = "zotero-profile-wide"
                used_queries.append(f"{key}:{query_for_log}")
                all_papers.extend(papers)
            except Exception as exc:
                logger.exception("Fetch failed: source=%s query=%s error=%s", source_name, query, exc)
    return all_papers, used_queries


def main() -> None:
    settings = Settings.from_env()
    date_str = local_date_string(settings.report_timezone)
    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    zotero_records: list[ZoteroRecord] = []
    auto_queries: list[str] = []
    if settings.has_zotero_profile:
        zotero_records = fetch_zotero_records(settings)
        logger.info("Loaded %d Zotero records for similarity profile.", len(zotero_records))
        if not zotero_records:
            logger.warning("Zotero profile is configured but no items were loaded.")
        auto_queries = build_seed_queries(
            zotero_records,
            count=settings.zotero_seed_query_count,
            terms_per_query=settings.zotero_seed_terms_per_query,
        )
        if auto_queries:
            logger.info("Generated %d auto queries from Zotero profile.", len(auto_queries))

    raw_papers, used_queries = collect_papers(settings, auto_queries, use_profile=bool(zotero_records))
    if zotero_records:
        engine = SimilarityEngine.from_records(zotero_records, reference_max=settings.similarity_reference_max)
        raw_papers = apply_similarity_filter(
            raw_papers,
            engine=engine,
            threshold=settings.similarity_threshold,
            min_shared_tokens=settings.similarity_min_shared_tokens,
        )
        logger.info("After Zotero similarity filtering: %d papers", len(raw_papers))

    final_papers = deduplicate_rank_limit(raw_papers, settings)
    grouped = group_by_source(final_papers)

    query_summary = used_queries or settings.topic_queries
    markdown = render_markdown(date_str, query_summary, grouped)
    html = render_html(date_str, query_summary, grouped)

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

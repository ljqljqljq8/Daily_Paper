from __future__ import annotations

import os
from dataclasses import dataclass


def _read_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _read_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    return int(raw)


def _read_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "y", "on"}


def _read_list(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default).strip()
    return [part.strip() for part in raw.split(",") if part.strip()]


def _split_queries(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(";") if part.strip()]


def _read_required_list(name: str) -> list[str]:
    values = _read_list(name, "")
    if not values:
        raise ValueError(f"Missing required environment variable: {name}")
    return values


@dataclass
class Settings:
    topic_queries: list[str]
    source_queries: dict[str, list[str]]
    enabled_sources: list[str]
    days_back: int
    max_results_per_query: int
    max_total_results: int
    send_empty_digest: bool
    dry_run: bool
    request_timeout: int
    user_agent: str
    smtp_server: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    email_sender: str
    email_receivers: list[str]
    ncbi_api_key: str
    serpapi_api_key: str
    report_timezone: str

    def queries_for_source(self, source: str) -> list[str]:
        return self.source_queries.get(source.lower().strip(), [])

    @classmethod
    def from_env(cls) -> "Settings":
        global_queries = _split_queries(os.getenv("TOPIC_QUERY", ""))
        source_queries = {
            "arxiv": _split_queries(os.getenv("ARXIV_QUERY", "")) or global_queries,
            "medrxiv": _split_queries(os.getenv("MEDRXIV_QUERY", "")) or global_queries,
            "pubmed": _split_queries(os.getenv("PUBMED_QUERY", "")) or global_queries,
            "scholar": _split_queries(os.getenv("SCHOLAR_QUERY", "")) or global_queries,
        }
        if not any(source_queries.values()):
            raise ValueError(
                "Missing query config. Set at least one of TOPIC_QUERY, ARXIV_QUERY, MEDRXIV_QUERY, PUBMED_QUERY, SCHOLAR_QUERY."
            )

        merged: list[str] = []
        seen: set[str] = set()
        for source in ["arxiv", "medrxiv", "pubmed", "scholar"]:
            for query in source_queries[source]:
                key = query.strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    merged.append(query)

        return cls(
            topic_queries=merged,
            source_queries=source_queries,
            enabled_sources=_read_list("ENABLE_SOURCES", "arxiv,medrxiv,pubmed,scholar"),
            days_back=_read_int("DAYS_BACK", 7),
            max_results_per_query=_read_int("MAX_RESULTS_PER_QUERY", 20),
            max_total_results=_read_int("MAX_TOTAL_RESULTS", 60),
            send_empty_digest=_read_bool("SEND_EMPTY_DIGEST", true),
            dry_run=_read_bool("DRY_RUN", False),
            request_timeout=_read_int("REQUEST_TIMEOUT", 20),
            user_agent=os.getenv("USER_AGENT", "daily-paper-bot/1.0 (+github-action)"),
            smtp_server=_read_required("SMTP_SERVER"),
            smtp_port=_read_int("SMTP_PORT", 465),
            smtp_username=_read_required("SMTP_USERNAME"),
            smtp_password=_read_required("SMTP_PASSWORD"),
            email_sender=_read_required("EMAIL_SENDER"),
            email_receivers=_read_required_list("EMAIL_RECEIVERS"),
            ncbi_api_key=os.getenv("NCBI_API_KEY", "").strip(),
            serpapi_api_key=os.getenv("SERPAPI_API_KEY", "").strip(),
            report_timezone=os.getenv("REPORT_TIMEZONE", "Asia/Shanghai").strip(),
        )

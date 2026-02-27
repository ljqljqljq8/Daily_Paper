from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


TOKEN_RE = re.compile(r"[a-zA-Z0-9]{3,}")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def in_recent_days(dt: datetime, days_back: int) -> bool:
    return dt >= now_utc() - timedelta(days=days_back)


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text or "")}


def relevance_score(query: str, title: str, abstract: str) -> float:
    q = tokenize(query)
    if not q:
        return 0.0
    title_tokens = tokenize(title)
    abstract_tokens = tokenize(abstract)
    title_hits = len(q & title_tokens)
    abstract_hits = len(q & abstract_tokens)
    return title_hits * 2.0 + abstract_hits * 1.0


def contains_query(query: str, title: str, abstract: str) -> bool:
    q_tokens = tokenize(query)
    if not q_tokens:
        return False
    haystack = tokenize(title) | tokenize(abstract)
    return len(haystack & q_tokens) > 0


def parse_date_best_effort(value: str) -> datetime:
    value = (value or "").strip()
    if not value:
        return now_utc()
    candidates = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y %b %d",
    ]
    for fmt in candidates:
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    m = re.search(r"(19|20)\d{2}", value)
    if m:
        return datetime(int(m.group(0)), 1, 1, tzinfo=timezone.utc)
    return now_utc()


def local_date_string(report_timezone: str) -> str:
    try:
        zone = ZoneInfo(report_timezone)
    except Exception:
        zone = timezone.utc
    return datetime.now(zone).strftime("%Y-%m-%d")


def utc_date_range(days_back: int) -> tuple[str, str]:
    end = now_utc().date()
    start = end - timedelta(days=max(days_back - 1, 0))
    return start.isoformat(), end.isoformat()


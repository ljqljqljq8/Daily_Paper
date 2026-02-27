from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import requests

from daily_paper.config import Settings


@dataclass
class ZoteroRecord:
    key: str
    title: str
    abstract: str
    tags: list[str]
    creators: list[str]
    publication: str
    year: str
    date_added: datetime | None

    @property
    def text(self) -> str:
        parts = [self.title, self.abstract, " ".join(self.tags), " ".join(self.creators), self.publication, self.year]
        return " ".join(part for part in parts if part).strip()


def fetch_zotero_records(settings: Settings) -> list[ZoteroRecord]:
    if not settings.has_zotero_profile:
        return []

    if settings.zotero_library_type not in {"user", "group"}:
        raise ValueError("ZOTERO_LIBRARY_TYPE must be 'user' or 'group'.")

    if settings.zotero_collection_key:
        base_url = (
            f"https://api.zotero.org/{settings.zotero_library_type}s/"
            f"{settings.zotero_library_id}/collections/{settings.zotero_collection_key}/items/top"
        )
    else:
        base_url = f"https://api.zotero.org/{settings.zotero_library_type}s/{settings.zotero_library_id}/items/top"

    headers = {
        "Zotero-API-Version": "3",
        "User-Agent": settings.user_agent,
    }
    if settings.zotero_api_key:
        headers["Zotero-API-Key"] = settings.zotero_api_key

    records: list[ZoteroRecord] = []
    start = 0
    page_size = 100
    target = max(settings.zotero_max_items, 1)
    while len(records) < target:
        limit = min(page_size, target - len(records))
        params = {
            "start": start,
            "limit": limit,
            "sort": "dateModified",
            "direction": "desc",
            "format": "json",
        }
        resp = requests.get(
            base_url,
            params=params,
            headers=headers,
            timeout=settings.request_timeout,
        )
        if resp.status_code in {401, 403}:
            raise ValueError(
                "Failed to access Zotero library. Check ZOTERO_LIBRARY_TYPE/ZOTERO_LIBRARY_ID/ZOTERO_API_KEY permissions."
            )
        resp.raise_for_status()
        items = resp.json()
        if not items:
            break
        for item in items:
            data = item.get("data", {})
            title = " ".join((data.get("title") or "").split())
            if not title:
                continue
            tags = []
            for tag in data.get("tags", []) or []:
                if isinstance(tag, dict):
                    name = (tag.get("tag") or "").strip()
                    if name:
                        tags.append(name)
            creators = []
            for creator in data.get("creators", []) or []:
                if not isinstance(creator, dict):
                    continue
                name = " ".join(
                    part
                    for part in [
                        (creator.get("firstName") or "").strip(),
                        (creator.get("lastName") or "").strip(),
                    ]
                    if part
                ).strip()
                if not name:
                    name = (creator.get("name") or "").strip()
                if name:
                    creators.append(name)
            records.append(
                ZoteroRecord(
                    key=(item.get("key") or "").strip(),
                    title=title,
                    abstract=" ".join((data.get("abstractNote") or "").split()),
                    tags=tags,
                    creators=creators,
                    publication=(data.get("publicationTitle") or "").strip(),
                    year=(data.get("date") or "").strip(),
                    date_added=_parse_zotero_datetime((data.get("dateAdded") or "").strip()),
                )
            )
            if len(records) >= target:
                break
        start += len(items)
        if len(items) < limit:
            break
    return records


def _parse_zotero_datetime(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


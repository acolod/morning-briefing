from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any

from .fetchers import SourceItem, fetch_sources


class SourcePool:
    def __init__(self) -> None:
        self.items: list[SourceItem] = []

    def add_items(self, items: list[SourceItem]) -> None:
        self.items.extend(items)

    async def fetch_all(self, fetchers: list[str]) -> list[SourceItem]:
        items = await asyncio.to_thread(fetch_sources, fetchers)
        self.add_items(items)
        return items

    def deduplicate(self, items: list[SourceItem]) -> list[SourceItem]:
        seen: set[str] = set()
        deduped: list[SourceItem] = []
        for item in items:
            if item.content_hash in seen:
                continue
            seen.add(item.content_hash)
            deduped.append(item)
        return deduped

    def normalize(self, items: list[SourceItem]) -> list[SourceItem]:
        return [
            SourceItem.create(
                title=item.title,
                url=item.url,
                source_name=item.source_name,
                source_type=item.source_type,
                published=item.published,
                description=item.description,
            )
            for item in items
        ]

    def reject_stale(self, items: list[SourceItem], max_age_hours: int = 48) -> list[SourceItem]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        kept: list[SourceItem] = []
        for item in items:
            published = _parse_datetime(item.published)
            if published is None or published >= cutoff:
                kept.append(item)
        return kept

    def sort_by_freshness(self, items: list[SourceItem]) -> list[SourceItem]:
        oldest = datetime.min.replace(tzinfo=timezone.utc)
        return sorted(
            items,
            key=lambda item: _parse_datetime(item.published) or oldest,
            reverse=True,
        )

    def filter_by_keywords(self, items: list[SourceItem], keywords: list[str]) -> list[SourceItem]:
        normalized_keywords = [keyword.casefold() for keyword in keywords if keyword.strip()]
        if not normalized_keywords:
            return items
        filtered: list[SourceItem] = []
        for item in items:
            haystack = f"{item.title} {item.description or ''}".casefold()
            if any(keyword in haystack for keyword in normalized_keywords):
                filtered.append(item)
        return filtered

    def to_json(self, items: list[SourceItem]) -> str:
        return json.dumps([asdict(item) for item in items], indent=2, sort_keys=True)

    @staticmethod
    def from_json(payload: str) -> list[SourceItem]:
        raw = json.loads(payload)
        if not isinstance(raw, list):
            raise ValueError("source pool JSON must be a list")
        return [SourceItem(**_source_item_dict(item)) for item in raw if isinstance(item, dict)]


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _source_item_dict(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": str(item.get("title", "")),
        "url": str(item.get("url", "")),
        "source_name": str(item.get("source_name", "")),
        "source_type": str(item.get("source_type", "")),
        "published": item.get("published") if item.get("published") is not None else None,
        "description": item.get("description") if item.get("description") is not None else None,
        "content_hash": str(item.get("content_hash", "")),
    }

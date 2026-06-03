from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Article:
    title: str
    url: str
    source: str
    description: str
    content_text: str
    date: str | None = None


SearchResult = Mapping[str, Any] | str
SearchFn = Callable[[str], Sequence[SearchResult]]
ExtractFn = Callable[[Sequence[str]], Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]]]


def gather(queries: Sequence[str], search_fn: SearchFn, extract_fn: ExtractFn) -> list[Article]:
    search_index: dict[str, dict[str, Any]] = {}
    for query in queries:
        try:
            search_results = search_fn(query)
        except Exception as exc:
            logger.warning("Search failed for query %r: %s", query, exc)
            continue
        for result in search_results or ():
            normalized = _normalize_search_result(result)
            if not normalized["url"]:
                continue
            search_index.setdefault(normalized["url"], {}).update(normalized)

    try:
        extracted = _normalize_extract_results(extract_fn(tuple(search_index.keys())))
    except Exception as exc:
        logger.warning("Article extraction failed: %s", exc)
        extracted = {}
    articles: list[Article] = []
    for url, search_meta in search_index.items():
        extracted_meta = extracted.get(url, {})
        extracted_date = _normalize_date(extracted_meta.get("date"))
        merged = {**search_meta, **extracted_meta, "url": url}
        merged["date"] = extracted_date or search_meta.get("date")
        articles.append(
            Article(
                title=str(merged.get("title", "Untitled article")),
                url=url,
                source=str(merged.get("source", _source_from_url(url))),
                description=str(merged.get("description", "")),
                content_text=str(merged.get("content_text") or merged.get("content") or ""),
                date=_normalize_date(merged.get("date")),
            )
        )
    return articles


def _normalize_search_result(result: SearchResult) -> dict[str, Any]:
    if isinstance(result, str):
        return {"url": result, "title": "", "source": _source_from_url(result), "description": "", "date": None}
    return {
        "url": str(result.get("url", "")),
        "title": str(result.get("title", "")),
        "source": str(result.get("source", _source_from_url(str(result.get("url", ""))))),
        "description": str(result.get("description", "")),
        "date": _normalize_date(result.get("date")),
    }


def _normalize_extract_results(
    extracted: Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    if isinstance(extracted, Mapping):
        return {str(url): dict(payload) for url, payload in extracted.items()}
    normalized: dict[str, dict[str, Any]] = {}
    for payload in extracted:
        url = str(payload.get("url", ""))
        if url:
            normalized[url] = dict(payload)
    return normalized


def _normalize_date(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _source_from_url(url: str) -> str:
    host = url.split("//")[-1].split("/")[0]
    return host.replace("www.", "") or "Unknown source"

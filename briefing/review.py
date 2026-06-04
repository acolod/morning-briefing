from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from .verify_urls import URL_RE, _url_is_live


_VALID_TAGS = {"adopt", "try", "track", "note"}


@dataclass
class ReviewReport:
    total_items: int
    dead_urls: list[str]
    missing_fields: list[str]
    duplicate_headlines: list[str]
    source_diversity: bool
    tag_distribution: dict
    passed: bool


def review_editorial(editorial: dict) -> ReviewReport:
    """Run automated checks on editorial JSON before rendering."""
    top_story = _mapping(editorial.get("top_story"))
    signals = [dict(item) for item in _list(editorial.get("signals")) if isinstance(item, Mapping)]
    radar = _list(editorial.get("radar"))
    stories = [top_story, *signals] if top_story else signals

    missing_fields = _missing_fields(top_story, signals)
    duplicate_headlines = _duplicate_headlines(stories)
    dead_urls = _dead_urls(editorial)
    source_diversity = len({_source_name(item) for item in stories if _source_name(item)}) >= 3
    tag_distribution = _tag_distribution(stories)
    tag_mix = sum(1 for count in tag_distribution.values() if count > 0) >= 2
    bad_placeholders = _placeholder_urls(editorial)
    missing_fields.extend(bad_placeholders)

    passed = not dead_urls and not missing_fields and not duplicate_headlines and source_diversity and tag_mix
    return ReviewReport(
        total_items=len(stories) + len(radar),
        dead_urls=dead_urls,
        missing_fields=missing_fields,
        duplicate_headlines=duplicate_headlines,
        source_diversity=source_diversity,
        tag_distribution=tag_distribution,
        passed=passed,
    )


def format_review_report(report: ReviewReport) -> str:
    status = "PASS" if report.passed else "FAIL"
    lines = [
        f"Review: {status}",
        f"- total_items: {report.total_items}",
        f"- dead_urls: {len(report.dead_urls)}",
        f"- missing_fields: {len(report.missing_fields)}",
        f"- duplicate_headlines: {len(report.duplicate_headlines)}",
        f"- source_diversity: {report.source_diversity}",
        f"- tag_distribution: {report.tag_distribution}",
    ]
    for url in report.dead_urls:
        lines.append(f"  dead: {url}")
    for field in report.missing_fields:
        lines.append(f"  missing: {field}")
    for headline in report.duplicate_headlines:
        lines.append(f"  duplicate: {headline}")
    return "\n".join(lines)


def _missing_fields(top_story: Mapping[str, Any], signals: list[dict[str, Any]]) -> list[str]:
    missing: list[str] = []
    for field in ("headline", "source", "url", "take", "tag"):
        if not _text(top_story.get(field)):
            missing.append(f"top_story.{field}")
    for index, signal in enumerate(signals):
        for field in ("headline", "source", "url", "take", "tag"):
            if not _text(signal.get(field)):
                missing.append(f"signals[{index}].{field}")
    return missing


def _duplicate_headlines(stories: list[Mapping[str, Any]]) -> list[str]:
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for story in stories:
        headline = _text(story.get("headline"))
        normalized = re.sub(r"[^a-z0-9]+", " ", headline.casefold()).strip()
        if not normalized:
            continue
        if normalized in seen:
            duplicates.append(headline)
        else:
            seen[normalized] = headline
    return duplicates


def _dead_urls(editorial: Mapping[str, Any]) -> list[str]:
    dead: list[str] = []
    for url in _all_urls(editorial):
        is_live, _reason = _url_is_live(url, timeout=5)
        if not is_live:
            dead.append(url)
    return dead


def _all_urls(editorial: Mapping[str, Any]) -> list[str]:
    urls: list[str] = []
    top_story = _mapping(editorial.get("top_story"))
    if _text(top_story.get("url")):
        urls.append(_text(top_story.get("url")))
    for signal in _list(editorial.get("signals")):
        if isinstance(signal, Mapping) and _text(signal.get("url")):
            urls.append(_text(signal.get("url")))
    for radar_item in _list(editorial.get("radar")):
        urls.extend(URL_RE.findall(_text(radar_item)))
    return urls


def _placeholder_urls(editorial: Mapping[str, Any]) -> list[str]:
    encoded = json.dumps(editorial)
    placeholders: list[str] = []
    if re.search(r'"url"\s*:\s*"#"', encoded):
        placeholders.append('url="#"')
    if re.search(r'"url"\s*:\s*""', encoded):
        placeholders.append('url=""')
    return placeholders


def _tag_distribution(stories: list[Mapping[str, Any]]) -> dict:
    distribution = {tag: 0 for tag in ("adopt", "try", "track", "note")}
    for story in stories:
        tag = _text(story.get("tag")).casefold()
        if tag in _VALID_TAGS:
            distribution[tag] += 1
    return distribution


def _source_name(item: Mapping[str, Any]) -> str:
    return _text(item.get("source")).casefold()


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""

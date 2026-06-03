from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import BriefingConfig, load_config


_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_TEMPLATE_NAME = "daily-brief.html"
_VALID_TAGS = {"adopt", "try", "track", "note"}


def render(
    editorial: Mapping[str, Any] | None,
    config: BriefingConfig | None = None,
    as_of: datetime | None = None,
) -> str:
    config = config or load_config()
    normalized = _normalize_editorial(editorial or {}, config, as_of=as_of)

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(_TEMPLATE_NAME)
    return template.render(**normalized)


def _normalize_editorial(
    editorial: Mapping[str, Any],
    config: BriefingConfig,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    zone = ZoneInfo(config.render.timezone)
    now = (as_of or datetime.now(timezone.utc)).astimezone(zone)
    issue_raw = _mapping(editorial.get("issue"))
    issue = {
        "number": _int_value(issue_raw.get("number"), 1),
        "date": _text(issue_raw.get("date")) or now.strftime("%B %-d, %Y"),
        "time": _text(issue_raw.get("time")) or now.strftime("%-I:%M %p %Z"),
        "sources_scanned": _int_value(issue_raw.get("sources_scanned"), 0),
        "articles_read": _int_value(issue_raw.get("articles_read"), 0),
    }

    top_story = _normalize_story(
        _mapping(editorial.get("top_story")),
        fallback_headline="No top story supplied.",
        fallback_take="The editorial JSON did not include a top story.",
        fallback_tag="note",
    )
    signals = [
        _normalize_story(_mapping(item), fallback_tag="note")
        for item in _list(editorial.get("signals"))[:6]
    ]
    radar = [_text(item) for item in _list(editorial.get("radar")) if _text(item)]
    one_move = _text(editorial.get("one_move")) or "No move supplied for this issue."

    return {
        "title": config.render.title,
        "issue_prefix": config.render.issue_prefix,
        "issue": issue,
        "top_story": top_story,
        "signals": signals,
        "radar": radar,
        "one_move": one_move,
        "metadata": {
            "date": issue["date"],
            "published": issue["time"],
            "issue_number": issue["number"],
        },
        "toprail": {
            "version": config.render.version,
            "sources_scanned": issue["sources_scanned"],
            "articles_read": issue["articles_read"],
        },
        "footrail": {
            "version": config.render.version,
            "tags": _visible_tags(top_story, signals),
        },
        "footer_note": config.render.footer_note,
    }


def _normalize_story(
    raw: Mapping[str, Any],
    fallback_headline: str = "Untitled signal.",
    fallback_take: str = "No editorial take supplied.",
    fallback_tag: str = "note",
) -> dict[str, str]:
    tag = _text(raw.get("tag")).lower()
    if tag not in _VALID_TAGS:
        tag = fallback_tag
    return {
        "headline": _text(raw.get("headline")) or fallback_headline,
        "source": _text(raw.get("source")) or "Unknown source",
        "url": _real_url(_text(raw.get("url"))),
        "take": _text(raw.get("take")) or fallback_take,
        "tag": tag,
        "tag_label": tag.upper(),
        "why_now": _text(raw.get("why_now")),
    }


def _visible_tags(top_story: Mapping[str, str], signals: list[Mapping[str, str]]) -> list[str]:
    tags = [top_story.get("tag", "note"), *(signal.get("tag", "note") for signal in signals)]
    return [tag for tag in ("adopt", "try", "track", "note") if tag in tags] or ["note"]


def _real_url(url: str) -> str:
    if url.startswith(("https://", "http://")) and url not in {"http://", "https://"}:
        return url
    return ""


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _int_value(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback

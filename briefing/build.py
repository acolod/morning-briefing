from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from .config import load_config
from .render import render
from .review import format_review_report, review_editorial
from .verify_urls import verify_urls


_DEMO_BANNER = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 320'%3E"
    "%3Crect width='1200' height='320' fill='%23060606'/%3E"
    "%3Cpath d='M0 230 L220 80 L440 190 L680 70 L930 180 L1200 55 L1200 320 L0 320 Z' "
    "fill='%23f4a84d' fill-opacity='0.20'/%3E"
    "%3Ccircle cx='930' cy='94' r='58' fill='%236ba0ff' fill-opacity='0.35'/%3E"
    "%3Cpath d='M120 248 H1080' stroke='%23ffd7a4' stroke-opacity='0.35' stroke-width='2'/%3E"
    "%3C/svg%3E"
)


_DEMO_EDITORIAL: dict[str, Any] = {
    "banner_image_url": _DEMO_BANNER,
    "issue": {
        "number": 1,
        "date": "June 5, 2026",
        "time": "6:30 AM PT",
        "sources_scanned": 28,
        "articles_read": 9,
    },
    "top_story": {
        "headline": "Example of today's top story with a real headline",
        "source": "Example Publication",
        "url": "https://example.com/",
        "date": "June 5, 2026",
        "take": "Example personal take explaining why this matters for the reader's build.",
        "tag": "adopt",
        "why_now": "Example timing context explaining why this is relevant now.",
    },
    "signals": [
        {
            "headline": "Example signal item with a clear title",
            "source": "Source Name",
            "url": "https://example.com/",
            "date": "June 5, 2026",
            "take": "Example one-sentence take with personal relevance.",
            "tag": "try",
        },
        {
            "headline": "Another example signal with different tag",
            "source": "Another Source",
            "url": "https://example.com/",
            "date": "June 5, 2026",
            "take": "Example take showing how this connects to the reader's stack.",
            "tag": "track",
        },
        {
            "headline": "Example for background context",
            "source": "Industry News",
            "url": "https://example.com/",
            "date": "June 5, 2026",
            "take": "Example contextual note with no immediate action required.",
            "tag": "note",
        },
        {
            "headline": "Example adopt signal for an immediate workflow update",
            "source": "Platform Notes",
            "url": "https://example.com/",
            "date": "June 5, 2026",
            "take": "Example adopt item that should change today's operating checklist.",
            "tag": "adopt",
        },
        {
            "headline": "Example prototype opportunity for local agent tooling",
            "source": "Tooling Lab",
            "url": "https://example.com/",
            "date": "June 5, 2026",
            "take": "Example quick experiment that can be tried without derailing the morning.",
            "tag": "try",
        },
        {
            "headline": "Example model runtime signal worth tracking",
            "source": "Inference Weekly",
            "url": "https://example.com/",
            "date": "June 5, 2026",
            "take": "Example runtime context that may affect near-term hardware choices.",
            "tag": "track",
        },
        {
            "headline": "Example note on ecosystem direction",
            "source": "Agent Systems Review",
            "url": "https://example.com/",
            "date": "June 5, 2026",
            "take": "Example background note that informs priorities without needing action.",
            "tag": "note",
        },
    ],
    "radar": [
        "Example radar item — a trend worth watching over time",
        "Another radar item with context about its significance",
        "Third radar item that stays brief and watch-oriented",
    ],
    "one_move": "Example concrete next action to take today, with rationale.",
}


def build(
    config_path: str | Path = "config.yaml",
    editorial_json_path: str | Path | None = None,
    editorial: Mapping[str, Any] | None = None,
    articles: Sequence[Mapping[str, Any]] | None = None,
    articles_path: str | Path | None = None,
    demo: bool = False,
    verify_links: bool = False,
    review: bool = False,
    **_unused_compat: Any,
) -> str:
    config = load_config(config_path)
    if editorial is not None:
        payload = dict(editorial)
    elif editorial_json_path is not None:
        payload = _load_editorial_json(Path(editorial_json_path))
    elif demo:
        payload = copy.deepcopy(_DEMO_EDITORIAL)
    elif articles is not None:
        payload = _editorial_from_articles(articles)
    elif articles_path is not None:
        payload = _editorial_from_articles(_load_articles(Path(articles_path)))
    else:
        raise ValueError("Provide --editorial-json FILE or use --demo.")
    if review:
        report = review_editorial(payload)
        print(format_review_report(report), file=sys.stderr)
        if not report.passed:
            raise ValueError("Editorial review failed.")
    if verify_links:
        payload = verify_urls(payload)
        _print_verification_warnings(payload)
    return render(payload, config=config)


def _load_editorial_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        print(f"Warning: could not load editorial JSON from {path}: {exc}", file=sys.stderr)
        return copy.deepcopy(_DEMO_EDITORIAL)
    if not isinstance(raw, dict):
        print(f"Warning: could not load editorial JSON from {path}: expected an object", file=sys.stderr)
        return copy.deepcopy(_DEMO_EDITORIAL)
    return raw


def _load_articles(path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        print(f"Warning: could not load articles from {path}: {exc}", file=sys.stderr)
        return []
    if not isinstance(raw, list):
        return []
    return [dict(item) for item in raw if isinstance(item, Mapping)]


def _editorial_from_articles(articles: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    editorial = copy.deepcopy(_DEMO_EDITORIAL)
    if not articles:
        return editorial
    lead = articles[0]
    editorial["top_story"] = _article_to_story(lead, "adopt")
    editorial["signals"] = [_article_to_story(article, "try") for article in articles[1:7]]
    editorial["issue"]["articles_read"] = len(articles)
    editorial["issue"]["sources_scanned"] = len({str(article.get("source", "")) for article in articles if article.get("source")})
    return editorial


def _article_to_story(article: Mapping[str, Any], tag: str) -> dict[str, str]:
    description = str(article.get("description") or article.get("content_text") or "").strip()
    return {
        "headline": str(article.get("title") or "Untitled source").strip(),
        "source": str(article.get("source") or "Unknown source").strip(),
        "url": str(article.get("url") or "https://example.com").strip(),
        "date": str(article.get("date") or article.get("published") or "").strip(),
        "take": description or "Source supplied without an editorial take.",
        "tag": tag,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Morning AI Briefing HTML artifact.")
    parser.add_argument("--config", default="config.yaml", help="Path to the YAML config file.")
    parser.add_argument("--editorial-json", type=str, default=None, help="Path to editorial JSON to render.")
    parser.add_argument("--demo", action="store_true", help="Render built-in sample editorial content.")
    parser.add_argument("--articles-file", type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--verify-links", action="store_true", help="Verify links and remove dead signal/radar items.")
    parser.add_argument("--review", action="store_true", help="Run automated editorial review before rendering.")
    parser.add_argument("--output", type=str, default=None, help="Write HTML to FILE atomically instead of stdout.")
    args = parser.parse_args(argv)

    try:
        html = build(
            config_path=args.config,
            editorial_json_path=args.editorial_json,
            articles_path=args.articles_file,
            demo=args.demo,
            verify_links=args.verify_links,
            review=args.review,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.output:
        _write_atomic(Path(args.output), html)
    else:
        sys.stdout.write(html)
        if not html.endswith("\n"):
            sys.stdout.write("\n")
    return 0


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = temp_file.name
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def _print_verification_warnings(payload: Mapping[str, Any]) -> None:
    report = payload.get("verification_report") if isinstance(payload, Mapping) else None
    if not isinstance(report, Mapping):
        return
    removed = report.get("removed")
    if not isinstance(removed, list):
        return
    for item in removed:
        if not isinstance(item, Mapping):
            continue
        print(
            "Warning: removed dead link "
            f"{item.get('url', '')} at {item.get('path', 'unknown')} ({item.get('reason', 'unreachable')})",
            file=sys.stderr,
        )


if __name__ == "__main__":
    raise SystemExit(main())

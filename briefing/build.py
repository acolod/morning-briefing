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


_DEMO_EDITORIAL: dict[str, Any] = {
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
        "url": "https://example.com/article",
        "take": "Example personal take explaining why this matters for the reader's build.",
        "tag": "adopt",
        "why_now": "Example timing context explaining why this is relevant now.",
    },
    "signals": [
        {
            "headline": "Example signal item with a clear title",
            "source": "Source Name",
            "url": "https://example.com/signal",
            "take": "Example one-sentence take with personal relevance.",
            "tag": "try",
        },
        {
            "headline": "Another example signal with different tag",
            "source": "Another Source",
            "url": "https://example.com/signal2",
            "take": "Example take showing how this connects to the reader's stack.",
            "tag": "track",
        },
        {
            "headline": "Example for background context",
            "source": "Industry News",
            "url": "https://example.com/signal3",
            "take": "Example contextual note with no immediate action required.",
            "tag": "note",
        },
    ],
    "radar": [
        "Example radar item — a trend worth watching over time",
        "Another radar item with context about its significance",
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
        "take": description or "Source supplied without an editorial take.",
        "tag": tag,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Morning AI Briefing HTML artifact.")
    parser.add_argument("--config", default="config.yaml", help="Path to the YAML config file.")
    parser.add_argument("--editorial-json", type=str, default=None, help="Path to editorial JSON to render.")
    parser.add_argument("--demo", action="store_true", help="Render built-in sample editorial content.")
    parser.add_argument("--articles-file", type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--output", type=str, default=None, help="Write HTML to FILE atomically instead of stdout.")
    args = parser.parse_args(argv)

    html = build(
        config_path=args.config,
        editorial_json_path=args.editorial_json,
        articles_path=args.articles_file,
        demo=args.demo,
    )
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


if __name__ == "__main__":
    raise SystemExit(main())

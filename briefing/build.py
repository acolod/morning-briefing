from __future__ import annotations

import json
import argparse
from pathlib import Path
from typing import Any, Sequence

from .config import load_config, load_momentum
from .gather import Article, gather
from .rank import rank
from .render import render


_DEMO_ARTICLES: tuple[dict[str, Any], ...] = (
    {
        "title": "Hermes agents get calmer tool memory and recovery loops",
        "url": "https://example.com/hermes-memory",
        "source": "Example Labs",
        "description": "Agent runs are getting more dependable because retry logic, memory, and browser handoffs are being treated as product features rather than incidental glue.",
        "content_text": "Hermes agents memory tool use browser workflows recovery loops automation reliability daily operations.",
        "date": "2026-06-03T11:00:00+00:00",
        "topics": ["hermes", "agents", "memory", "tooling"],
    },
    {
        "title": "CLI-first automation stacks are replacing one-off demo scaffolds",
        "url": "https://example.com/cli-automation",
        "source": "Builder Weekly",
        "description": "Developer workflows are consolidating around portable CLI tools, orchestration scripts, and repeatable local automation.",
        "content_text": "developer workflows cli tooling automation scripts orchestration portable local operations.",
        "date": "2026-06-03T08:20:00+00:00",
        "topics": ["developer", "tooling", "automation", "cli"],
    },
    {
        "title": "New model launches matter less than latency, price, and tool behavior",
        "url": "https://example.com/model-landscape",
        "source": "Inference Report",
        "description": "Benchmarks still move headlines, but product teams are filtering models through cost, latency, and tool-call quality first.",
        "content_text": "models pricing context windows benchmarks inference latency tool calls deployment tradeoffs.",
        "date": "2026-06-03T07:45:00+00:00",
        "topics": ["models", "benchmarks", "pricing"],
    },
    {
        "title": "Product builders are packaging AI features as disciplined daily loops",
        "url": "https://example.com/product-loops",
        "source": "Indie Product Notes",
        "description": "The strongest AI products are narrowing around recurring operator actions instead of sprawling feature collections.",
        "content_text": "product building shipping design workflow leverage indie development daily loop experiments.",
        "date": "2026-06-02T22:00:00+00:00",
        "topics": ["product", "shipping", "build"],
    },
    {
        "title": "Voice agents are improving, but workflow fit still decides adoption",
        "url": "https://example.com/voice-fit",
        "source": "Audio Futures",
        "description": "Speech quality is rising quickly, yet teams still need clear reasons to insert voice into real operator workflows.",
        "content_text": "voice audio agents speech interfaces workflow fit adoption tts transcription.",
        "date": "2026-06-02T18:30:00+00:00",
        "topics": ["voice", "audio"],
    },
    {
        "title": "Video generation tooling is getting more usable for fast concept work",
        "url": "https://example.com/video-gen",
        "source": "Visual Systems",
        "description": "ComfyUI-style pipelines are becoming practical for quick internal concept passes even if they are still too messy for broad deployment.",
        "content_text": "video generation comfyui diffusion workflow concept art tooling experimentation.",
        "date": "2026-06-02T16:10:00+00:00",
        "topics": ["video", "visual", "comfyui"],
    },
)

_DEFAULT_MOMENTUM = {
    "hermetic_agents": 1.0,
    "dev_tooling": 0.8,
    "product_building": 0.6,
}


def build(
    config_path: str | Path = "config.yaml",
    momentum_path: str | Path | None = "momentum.json",
    articles_path: str | Path | None = None,
    search_fn=None,
    extract_fn=None,
    demo: bool = False,
) -> str:
    config = load_config(config_path)
    momentum = load_momentum(momentum_path)
    if demo and not momentum:
        momentum = dict(_DEFAULT_MOMENTUM)

    if demo:
        search_fn = _demo_search
        extract_fn = _demo_extract

    if articles_path:
        articles = _load_articles(Path(articles_path))
    elif search_fn is not None and extract_fn is not None:
        articles = gather(config.search_queries, search_fn=search_fn, extract_fn=extract_fn)
    else:
        raise ValueError("Production mode requires either --articles-file or injected search_fn and extract_fn callbacks.")

    ranked_articles = rank(articles, config, momentum=momentum)
    return render(ranked_articles, config, momentum=momentum)


def _load_articles(path: Path) -> list[Article]:
    """Load articles from a JSON file. Expects a list of dicts with fields:
    title, url, source, description, content_text, date (optional)."""
    with open(path) as f:
        raw = json.load(f)
    return [
        Article(
            title=str(item.get("title", "")),
            url=str(item.get("url", "")),
            source=str(item.get("source", "")),
            description=str(item.get("description", "")),
            content_text=str(item.get("content_text", "")),
            date=str(item["date"]) if item.get("date") else None,
        )
        for item in raw
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Morning AI Briefing HTML artifact.")
    parser.add_argument("--config", default="config.yaml", help="Path to the YAML config file.")
    parser.add_argument("--momentum", default="momentum.json", help="Path to the optional momentum JSON file.")
    parser.add_argument("--demo", action="store_true", help="Use built-in sample content instead of injected callbacks.")
    parser.add_argument("--articles-file", type=str, default=None, help="Path to a JSON file with pre-collected articles (bypasses gather).")
    args = parser.parse_args(argv)

    html = build(
        config_path=args.config,
        momentum_path=args.momentum,
        articles_path=args.articles_file,
        demo=args.demo,
    )
    print(html)
    return 0


def _demo_search(query: str) -> list[dict[str, Any]]:
    query_text = query.lower()
    matches = []
    for article in _DEMO_ARTICLES:
        haystack = " ".join(article["topics"]) + " " + article["title"].lower() + " " + article["description"].lower()
        if any(token in haystack for token in query_text.split()):
            matches.append(
                {
                    "title": article["title"],
                    "url": article["url"],
                    "source": article["source"],
                    "description": article["description"],
                    "date": article["date"],
                }
            )
    return matches or [
        {
            "title": article["title"],
            "url": article["url"],
            "source": article["source"],
            "description": article["description"],
            "date": article["date"],
        }
        for article in _DEMO_ARTICLES[:3]
    ]


def _demo_extract(urls: Sequence[str]) -> dict[str, dict[str, Any]]:
    lookup = {article["url"]: article for article in _DEMO_ARTICLES}
    return {
        url: {
            "url": url,
            "title": lookup[url]["title"],
            "source": lookup[url]["source"],
            "description": lookup[url]["description"],
            "content_text": lookup[url]["content_text"],
            "date": lookup[url]["date"],
        }
        for url in urls
        if url in lookup
    }


if __name__ == "__main__":
    raise SystemExit(main())
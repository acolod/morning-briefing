from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class CategoryConfig:
    weight: float
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class RankingConfig:
    recency_half_life_days: float
    recency_boost: float
    stale_interest_decay: float
    momentum_multiplier: float
    top_signals: int


@dataclass(frozen=True)
class RenderConfig:
    source_window: str
    timezone: str
    issue_prefix: str
    title: str
    footer_note: str


@dataclass(frozen=True)
class BriefingConfig:
    search_queries: tuple[str, ...]
    categories: dict[str, CategoryConfig]
    ranking: RankingConfig
    render: RenderConfig


def load_config(path: str | Path) -> BriefingConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    categories = {
        name: CategoryConfig(
            weight=float(settings["weight"]),
            keywords=tuple(str(keyword).lower() for keyword in settings.get("keywords", [])),
        )
        for name, settings in raw["categories"].items()
    }
    ranking = RankingConfig(
        recency_half_life_days=float(raw["ranking"]["recency_half_life_days"]),
        recency_boost=float(raw["ranking"]["recency_boost"]),
        stale_interest_decay=float(raw["ranking"]["stale_interest_decay"]),
        momentum_multiplier=float(raw["ranking"]["momentum_multiplier"]),
        top_signals=int(raw["ranking"].get("top_signals", 4)),
    )
    render = RenderConfig(
        source_window=str(raw["render"]["source_window"]),
        timezone=str(raw["render"]["timezone"]),
        issue_prefix=str(raw["render"].get("issue_prefix", "Issue")),
        title=str(raw["render"].get("title", "Morning AI Brief")),
        footer_note=str(raw["render"]["footer_note"]),
    )
    return BriefingConfig(
        search_queries=tuple(str(query) for query in raw.get("search_queries", [])),
        categories=categories,
        ranking=ranking,
        render=render,
    )


def load_momentum(path: str | Path | None) -> dict[str, float]:
    if path is None:
        return {}
    momentum_path = Path(path)
    if not momentum_path.exists():
        return {}
    raw = json.loads(momentum_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "topics" in raw:
        raw = raw["topics"]
    if not isinstance(raw, dict):
        return {}
    return {str(key): float(value) for key, value in raw.items()}


def category_names(config: BriefingConfig) -> tuple[str, ...]:
    return tuple(config.categories.keys())


def category_keywords(config: BriefingConfig) -> dict[str, tuple[str, ...]]:
    return {name: details.keywords for name, details in config.categories.items()}


def category_weights(config: BriefingConfig) -> dict[str, float]:
    return {name: details.weight for name, details in config.categories.items()}

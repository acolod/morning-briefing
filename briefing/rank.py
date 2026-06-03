from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Sequence

from .config import BriefingConfig
from .gather import Article


@dataclass(frozen=True)
class RankedArticle:
    article: Article
    score: float
    category: str
    matched_keywords: tuple[str, ...]
    days_old: float


def rank(
    articles: Sequence[Article],
    config: BriefingConfig,
    momentum: dict[str, float] | None = None,
    now: datetime | None = None,
) -> list[RankedArticle]:
    momentum = momentum or {}
    now = now or datetime.now(timezone.utc)
    ranked: list[RankedArticle] = []
    for article in articles:
        ranked.append(_score_article(article, config, momentum, now))
    return sorted(ranked, key=lambda article: article.score, reverse=True)


def _score_article(
    article: Article,
    config: BriefingConfig,
    momentum: dict[str, float],
    now: datetime,
) -> RankedArticle:
    text = " ".join(part for part in [article.title, article.description, article.content_text] if part).lower()
    days_old = _days_old(article.date, now)
    recency_bonus = config.ranking.recency_boost / (1.0 + (days_old / max(config.ranking.recency_half_life_days, 0.1)))
    decay_penalty = days_old * config.ranking.stale_interest_decay

    best_category = "general_ai"
    best_score = float("-inf")
    best_keywords: tuple[str, ...] = ()

    for name, category in config.categories.items():
        matched = tuple(keyword for keyword in category.keywords if keyword in text)
        keyword_score = float(len(matched))
        weighted_score = keyword_score * category.weight
        momentum_bonus = momentum.get(name, 0.0) * config.ranking.momentum_multiplier
        score = weighted_score + recency_bonus + momentum_bonus - decay_penalty
        if score > best_score:
            best_score = score
            best_category = name
            best_keywords = matched

    return RankedArticle(
        article=article,
        score=round(best_score, 4),
        category=best_category,
        matched_keywords=best_keywords,
        days_old=round(days_old, 3),
    )


def _days_old(date_text: str | None, now: datetime) -> float:
    if not date_text:
        return 1.0
    parsed = _parse_datetime(date_text)
    if parsed is None:
        return 1.0
    delta = now - parsed
    return max(delta.total_seconds() / 86400.0, 0.0)


def _parse_datetime(value: str) -> datetime | None:
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

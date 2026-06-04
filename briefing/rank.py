from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence

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
    config: Any | None = None,
    momentum: dict[str, float] | None = None,
    now: datetime | None = None,
) -> list[RankedArticle]:
    """Compatibility scorer retained for callers outside the renderer path."""
    momentum = momentum or {}
    now = now or datetime.now(timezone.utc)
    ranked: list[RankedArticle] = []
    for article in articles:
        ranked.append(_score_article(article, config, momentum, now))
    return sorted(ranked, key=lambda article: article.score, reverse=True)


def _score_article(
    article: Article,
    config: Any | None,
    momentum: dict[str, float],
    now: datetime,
) -> RankedArticle:
    text = " ".join(part for part in [article.title, article.description, article.content_text] if part).lower()
    days_old = _days_old(article.date, now)
    matched_keywords = tuple(keyword for keyword in momentum if keyword.lower() in text)
    momentum_bonus = sum(momentum[keyword] for keyword in matched_keywords)
    recency_bonus = 1.0 / (1.0 + days_old)
    content_bonus = min(len(text) / 1000.0, 1.0)
    score = recency_bonus + content_bonus + momentum_bonus

    return RankedArticle(
        article=article,
        score=round(score, 4),
        category="compatibility",
        matched_keywords=matched_keywords,
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

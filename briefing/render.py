from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import BriefingConfig
from .rank import RankedArticle


_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_TEMPLATE_NAME = "daily-brief.html"


def render(
    articles: list[RankedArticle],
    config: BriefingConfig,
    momentum: dict[str, float] | None = None,
    as_of: datetime | None = None,
) -> str:
    momentum = momentum or {}
    zone = ZoneInfo(config.render.timezone)
    now = (as_of or datetime.now(timezone.utc)).astimezone(zone)
    top_articles = articles[: max(config.ranking.top_signals, 3)]
    top_categories = _category_counts(top_articles)
    rising_name = _rising_category(momentum, top_categories)

    context = {
        "issue": {
            "number": 1,
            "date": now.strftime("%B %-d, %Y") if hasattr(now, "strftime") else "",
            "day": now.strftime("%A"),
            "time": now.strftime("%-I:%M %p %Z"),
            "headline": _headline(top_articles),
            "lede": _lede(top_articles),
            "theme_line": _theme_line(top_articles),
            "source_window": config.render.source_window,
        },
        "hero_cards": _hero_cards(top_articles, rising_name),
        "signals": [
            {
                "number": f"{index:02d}",
                "headline": article.article.title,
                "tag": _signal_tag(article),
                "why": _why_it_matters(article),
            }
            for index, article in enumerate(top_articles, start=1)
        ],
        "build_journey": _build_journey(top_categories, top_articles),
        "rising_topic": {
            "name": _label_for_category(rising_name),
            "body": _rising_body(rising_name, momentum.get(rising_name, 0.0), top_categories),
        },
        "rising_details": [
            {
                "eyebrow": "Weighting",
                "title": "Stable interests + recent mentions + follow-up depth - decay",
                "body": "The score blends static preferences with recency and momentum so the brief can visibly rebalance without losing its core lanes.",
            },
            {
                "eyebrow": "Effect",
                "title": "Changes the sources, section order, and suggested experiments",
                "body": "The ranking should shift what rises, what stays persistent, and what is framed as worth testing today.",
            },
        ],
        "radar_items": _radar_items(articles),
        "moves": _moves(top_articles, rising_name),
        "image_treatment": {
            "rule_title": "Use at most one or two visuals in an issue.",
            "rule_body": "Good candidates: a compact article image, chart crop, product screenshot, or a restrained abstract illustration that supports the lead theme.",
            "placement_title": "Best slots are the top-right rail or a mid-page story callout.",
            "placement_body": "That keeps the page feeling premium and alive without turning the brief into a thumbnail feed.",
            "article_slot_eyebrow": "Article image mock slot",
            "article_slot_title": "Example of a tiny extracted visual card.",
            "article_slot_body": "A production version can pull a clean source image from the most relevant article or fall back to an abstract visual if the source art is noisy.",
        },
        "delivery_path": [
            "Hosted HTML artifact + Telegram link",
            "Attachment fallback while setup is still local",
            "Email only as a secondary archive channel later",
        ],
        "visual_rules": [
            {
                "eyebrow": "Tone",
                "title": "Polished first, retro second.",
                "body": "The aesthetic can nod to terminal energy without sacrificing a calm, modern reading experience.",
            },
            {
                "eyebrow": "Scale",
                "title": "Titles stay strong without becoming oversized posters.",
                "body": "More premium desktop briefing, less giant splash screen.",
            },
        ],
        "metadata": {
            "date": now.strftime("%B %-d, %Y"),
            "published": now.strftime("%-I:%M %p %Z"),
            "source_window": config.render.source_window,
            "issue_id": "#001",
        },
        "toprail": {
            "path": f"/briefs/{now.strftime('%Y-%m-%d')}",
            "version": "v1 production",
            "mode": "builder",
            "signals_count": str(len(top_articles)),
            "delivery": "html-first",
            "assets": "restrained",
        },
        "footrail": {
            "version": "production v1",
            "traits": "dense / polished / adaptive / image-light",
            "tags": ["standalone html", "subtle motion", "dated footer", "mobile-openable"],
        },
        "visual_note": {
            "title": "Article-style visuals are the better fit here.",
            "body": "This keeps the image treatment feeling native to the briefing instead of looking like a detached hero asset or broken attachment.",
        },
        "metadata_idea": {
            "title": "Each issue should stamp its timing and input window clearly.",
            "body": "Date, publish time, timezone, source window, and issue ID make the brief feel archival and trustworthy.",
        },
        "footer_note": config.render.footer_note,
        "title": config.render.title,
    }

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=False,
        lstrip_blocks=False,
    )
    template = env.get_template(_TEMPLATE_NAME)
    return template.render(**context)


def _headline(articles: list[RankedArticle]) -> str:
    if not articles:
        return "Sharper filters. Better timing. Fewer wasted clicks."
    primary = articles[0].article.title.rstrip(".")
    if len(articles) == 1:
        return primary
    secondary = articles[1].article.title.rstrip(".")
    return f"{primary}. {secondary}."


def _lede(articles: list[RankedArticle]) -> str:
    if not articles:
        return "A focused morning pass that surfaces what is worth testing, what deserves tracking, and what can be ignored without guilt."
    fragments = [article.article.description.strip() for article in articles[:2] if article.article.description.strip()]
    if not fragments:
        fragments = [articles[0].article.content_text.strip()[:220].strip()]
    return " ".join(fragment.rstrip(".") + "." for fragment in fragments if fragment)


def _theme_line(articles: list[RankedArticle]) -> str:
    if not articles:
        return "The best morning issue is the one that reduces drag and clarifies what deserves attention right now."
    categories = ", ".join(_label_for_category(article.category) for article in articles[:3])
    return f"The highest-leverage signal today sits in {categories.lower()}, where practical workflow value matters more than novelty for its own sake."


def _hero_cards(articles: list[RankedArticle], rising_name: str) -> list[dict[str, str]]:
    lead = articles[0] if articles else None
    return [
        {
            "eyebrow": "Top lane",
            "title": lead.article.title if lead else "Reliability over raw novelty.",
            "body": "Make the first screen answer what is worth testing today, not just what happened.",
        },
        {
            "eyebrow": "Adaptive lane",
            "title": f"{_label_for_category(rising_name)} is shaping the brief.",
            "body": "Momentum should rise quickly when a topic keeps surfacing, then cool off naturally when attention moves elsewhere.",
        },
        {
            "eyebrow": "Delivery lane",
            "title": "The artifact is the product.",
            "body": "HTML carries the full reading surface while messaging remains a nudge and deep-link, not the main canvas.",
        },
    ]


def _build_journey(top_categories: Counter[str], articles: list[RankedArticle]) -> list[str]:
    bullets: list[str] = []
    for category, _count in top_categories.most_common(3):
        bullets.append(f"Keep {_label_for_category(category).lower()} visible as a persistent lane while the brief adapts around current spikes.")
    if articles:
        bullets.append(f"Promote action labels clearly: {_signal_tag(articles[0]).lower()} {articles[0].article.source} before adding more links.")
    bullets.append("Use fewer, better links so curation feels intentional rather than exhaustive.")
    return bullets[:4]


def _radar_items(articles: list[RankedArticle]) -> list[dict[str, str]]:
    radar = [article for article in articles if article.category in {"hermetic_agents", "dev_tooling"}]
    if not radar:
        radar = articles[:2]
    items = []
    for article in radar[:3]:
        items.append(
            {
                "eyebrow": "Radar",
                "title": article.article.title,
                "body": _why_it_matters(article),
            }
        )
    return items


def _moves(articles: list[RankedArticle], rising_name: str) -> list[dict[str, str]]:
    lead = articles[0] if articles else None
    follow = articles[1] if len(articles) > 1 else lead
    return [
        {
            "eyebrow": "Build path",
            "title": "Ship the first automated loop before overbuilding controls.",
            "body": f"Gather sources, score them, render the HTML artifact, and validate against {lead.article.title if lead else 'your top lane'} before widening the surface.",
        },
        {
            "eyebrow": "Learn next",
            "title": f"Study the ranking dynamics around {_label_for_category(rising_name).lower()}.",
            "body": f"Use {follow.article.title if follow else 'the lead signal'} as the next test case for recency and momentum tuning.",
        },
    ]


def _why_it_matters(article: RankedArticle) -> str:
    if article.article.description.strip():
        return article.article.description.strip().rstrip(".") + "."
    snippet = article.article.content_text.strip().split(".")[0].strip()
    if snippet:
        return snippet.rstrip(".") + "."
    return f"This signal is strongest in {_label_for_category(article.category).lower()} and scored {article.score:.2f} in the current pass."


def _signal_tag(article: RankedArticle) -> str:
    if article.category in {"hermetic_agents", "dev_tooling", "product_building"} and article.score >= 2.0:
        return "Test"
    if article.category in {"model_landscape", "general_ai", "voice_audio", "video_gen"}:
        return "Track"
    if article.score <= 0.75 or article.category == "legal_ai":
        return "Ignore"
    return "Learn"


def _category_counts(articles: list[RankedArticle]) -> Counter[str]:
    return Counter(article.category for article in articles)


def _rising_category(momentum: dict[str, float], top_categories: Counter[str]) -> str:
    if momentum:
        return max(momentum.items(), key=lambda item: item[1])[0]
    if top_categories:
        return top_categories.most_common(1)[0][0]
    return "general_ai"


def _rising_body(category: str, momentum_score: float, top_categories: Counter[str]) -> str:
    base = f"{_label_for_category(category)} is the strongest adaptive lane right now"
    if momentum_score:
        return f"{base}, with momentum {momentum_score:.2f}. Keep that topic visible while it still changes what is worth testing, tracking, or ignoring."
    if top_categories:
        return f"{base}, based on the current article mix. The section should expand when the topic stays sticky and cool off naturally when it fades."
    return f"{base}. This module proves the brief is alive rather than pinned to a static taxonomy forever."


def _label_for_category(name: str) -> str:
    return name.replace("_", " ").title()

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
        "signals": _signals(top_articles),
        "build_journey": _build_journey(top_categories, top_articles),
        "rising_topic": {
            "name": _label_for_category(rising_name),
            "body": _rising_body(rising_name, momentum.get(rising_name, 0.0), top_categories, top_articles),
        },
        "rising_details": _rising_details(rising_name, momentum.get(rising_name, 0.0), top_categories, top_articles),
        "radar_items": _radar_items(articles),
        "moves": _moves(top_articles, rising_name),
        "image_treatment": _image_treatment(top_articles),
        "delivery_path": _delivery_path(top_articles),
        "visual_rules": _visual_rules(top_articles),
        "metadata": {
            "date": now.strftime("%B %-d, %Y"),
            "published": now.strftime("%-I:%M %p %Z"),
            "source_window": config.render.source_window,
            "issue_id": f"#{now.strftime('%Y%m%d')}",
        },
        "toprail": {
            "path": f"/briefs/{now.strftime('%Y-%m-%d')}",
            "version": "v1 production",
            "mode": "builder",
            "signals_count": str(len(top_articles)),
            "delivery": "html-first",
            "assets": _asset_label(top_articles),
        },
        "footrail": {
            "version": "production v1",
            "traits": _footrail_traits(top_categories),
            "tags": _footrail_tags(top_articles),
        },
        "side_stack": _side_stack(top_articles, top_categories),
        "footer_note": _footer_note(config.render.footer_note, top_articles),
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
    categories = _join_human([_label_for_category(article.category).lower() for article in articles[:3]])
    sources = _join_human([_source(article) for article in articles[:2]])
    return f"Today's strongest thread connects {categories}; start with {sources} before widening the read."


def _hero_cards(articles: list[RankedArticle], rising_name: str) -> list[dict[str, str]]:
    if not articles:
        return [
            {
                "eyebrow": "No inputs",
                "title": "No articles landed in this run.",
                "body": "The brief rendered cleanly, but it needs a fresh article batch before it can make an editorial call.",
            }
        ]

    cards: list[dict[str, str]] = []
    for article in articles[:2]:
        cards.append(
            {
                "eyebrow": f"{_signal_tag(article)} // {_source(article)}",
                "title": article.article.title,
                "body": f"{_summary(article, 132)} Matched {_keyword_phrase(article)}; score {article.score:.2f}.",
            }
        )

    category_count = Counter(article.category for article in articles)
    category, count = category_count.most_common(1)[0]
    sources = _join_human([_source(article) for article in articles[:3]])
    cards.append(
        {
            "eyebrow": "Today's shape",
            "title": f"{_label_for_category(rising_name)} is the pressure point.",
            "body": f"{_label_for_category(category)} appears in {count} of {len(articles)} top signals, with evidence from {sources}.",
        }
    )
    return cards[:3]


def _signals(articles: list[RankedArticle]) -> list[dict[str, str | None]]:
    signals = []
    for index, article in enumerate(articles, start=1):
        signals.append(
            {
                "number": f"{index:02d}",
                "headline": article.article.title,
                "url": _real_url(article.article.url),
                "tag": _signal_tag(article),
                "why": _why_it_matters(article),
            }
        )
    return signals


def _build_journey(top_categories: Counter[str], articles: list[RankedArticle]) -> list[str]:
    bullets: list[str] = []
    if articles:
        lead = articles[0]
        bullets.append(
            f"Start with {_source(lead)}: turn '{_clip(lead.article.title, 72)}' into one concrete check before opening the rest of the queue."
        )
    for category, count in top_categories.most_common(3):
        bullets.append(
            f"Give {_label_for_category(category).lower()} {count} slot{'s' if count != 1 else ''}; that is where today's article mix is clustering."
        )
    if len(articles) > 1:
        bullets.append(
            f"Use {_source(articles[1])} as the counterweight so the issue does not overfit to the lead source."
        )
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
                "url": _real_url(article.article.url),
                "body": _why_it_matters(article),
            }
        )
    return items


def _moves(articles: list[RankedArticle], rising_name: str) -> list[dict[str, str]]:
    lead = articles[0] if articles else None
    follow = articles[1] if len(articles) > 1 else lead
    follow_category = _label_for_category(follow.category).lower() if follow else _label_for_category(rising_name).lower()
    follow_source = _source(follow) if follow else "the second source"
    follow_keywords = _keyword_phrase(follow) if follow else _label_for_category(rising_name).lower()
    return [
        {
            "eyebrow": f"{_signal_tag(lead) if lead else 'Check'} today",
            "title": f"Pressure-test {_clip(lead.article.title, 82) if lead else _label_for_category(rising_name)}.",
            "url": _real_url(lead.article.url) if lead else None,
            "body": f"Use {_source(lead) if lead else 'the lead source'} as the source of truth, then decide whether this belongs in the next build cycle.",
        },
        {
            "eyebrow": "Compare next",
            "title": f"Read the {follow_category} angle from {follow_source}.",
            "url": _real_url(follow.article.url) if follow else None,
            "body": f"Matched {follow_keywords}; use it to separate durable pattern from one-off headline.",
        },
    ]


def _why_it_matters(article: RankedArticle) -> str:
    summary = _summary(article, 210)
    metadata = (
        f"{_source(article)} landed in {_label_for_category(article.category).lower()} "
        f"with {_keyword_phrase(article)} matched, age {_freshness(article)}, score {article.score:.2f}."
    )
    if summary:
        return f"{summary} {metadata}"
    return metadata


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


def _rising_body(
    category: str,
    momentum_score: float,
    top_categories: Counter[str],
    articles: list[RankedArticle],
) -> str:
    base = f"{_label_for_category(category)} is the strongest adaptive lane right now"
    related = [article for article in articles if article.category == category] or articles[:2]
    evidence = _join_human([_source(article) for article in related[:3]])
    if momentum_score:
        return f"{base}, with momentum {momentum_score:.2f} and fresh evidence from {evidence}."
    if top_categories:
        count = top_categories.get(category, 0)
        return f"{base}, based on {count or len(related)} current signal{'s' if (count or len(related)) != 1 else ''} from {evidence}."
    return f"{base}, but there were no ranked articles to explain the movement."


def _label_for_category(name: str) -> str:
    return name.replace("_", " ").title()


def _rising_details(
    category: str,
    momentum_score: float,
    top_categories: Counter[str],
    articles: list[RankedArticle],
) -> list[dict[str, str]]:
    related = [article for article in articles if article.category == category] or articles[:2]
    lead = related[0] if related else None
    count = top_categories.get(category, len(related))
    details = [
        {
            "eyebrow": "Why it rose",
            "title": f"{count or 0} top signal{'s' if (count or 0) != 1 else ''} point at {_label_for_category(category).lower()}.",
            "body": (
                f"The clearest evidence is {_source(lead)} on '{_clip(lead.article.title, 86)}', "
                f"with {_keyword_phrase(lead)} matched."
                if lead
                else "No article evidence was available in this run."
            ),
        },
        {
            "eyebrow": "Momentum",
            "title": f"Current carryover is {momentum_score:.2f}.",
            "body": (
                "The lane is both in the stored momentum file and present in today's ranked articles."
                if momentum_score and count
                else "The lane is being pulled mainly by today's article mix, not older carryover."
            ),
        },
    ]
    if len(related) > 1:
        details.append(
            {
                "eyebrow": "Second proof",
                "title": _clip(related[1].article.title, 88),
                "body": f"{_source(related[1])} gives the backup read; score {related[1].score:.2f}, age {_freshness(related[1])}.",
            }
        )
    return details[:3]


def _image_treatment(articles: list[RankedArticle]) -> dict[str, str]:
    lead = articles[0] if articles else None
    support = articles[1] if len(articles) > 1 else lead
    if lead is None:
        return {
            "heading": "Story treatment",
            "kicker": "waiting for articles",
            "rule_eyebrow": "Lead evidence",
            "rule_title": "No article is available to anchor the issue.",
            "rule_body": "The renderer keeps this slot quiet until the gather step supplies a real source and URL.",
            "placement_eyebrow": "Backup read",
            "placement_title": "No secondary source was ranked.",
            "placement_body": "Once articles arrive, this module should explain why the second read changes the lead.",
            "article_slot_eyebrow": "Evidence cue",
            "article_slot_title": "Waiting for a source-backed visual.",
            "article_slot_body": "The issue needs a real article before a visual treatment can be chosen.",
        }
    return {
        "heading": "Story treatment",
        "kicker": f"{_source(lead)} lead",
        "rule_eyebrow": "Lead evidence",
        "rule_title": f"Anchor the issue on {_possessive(_source(lead))} {_label_for_category(lead.category).lower()} signal.",
        "rule_body": f"{_summary(lead, 170)} The strongest visual cue is {_keyword_phrase(lead)}, not generic AI imagery.",
        "placement_eyebrow": "Contrast",
        "placement_title": f"Use {_source(support) if support else _source(lead)} to widen the read.",
        "placement_body": (
            f"Pair the lead with '{_clip(support.article.title, 96)}' so the page shows both the headline claim and the practical consequence."
            if support
            else "No second article ranked high enough to create a contrast module."
        ),
        "article_slot_eyebrow": f"{_source(lead)} cue",
        "article_slot_title": _clip(lead.article.title, 96),
        "article_slot_body": f"Represent {_keyword_phrase(lead)} as compact evidence: source, category, score {lead.score:.2f}, and one sentence of context.",
    }


def _delivery_path(articles: list[RankedArticle]) -> list[dict[str, str]]:
    links = []
    for article in articles[:3]:
        url = _real_url(article.article.url)
        if not url:
            continue
        links.append(
            {
                "label": f"Read {_source(article)}",
                "url": url,
                "body": _clip(article.article.title, 92),
            }
        )
    return links


def _visual_rules(articles: list[RankedArticle]) -> list[dict[str, str]]:
    if not articles:
        return [
            {
                "eyebrow": "Empty run",
                "title": "Keep the page sparse until real sources arrive.",
                "body": "A daily brief should not invent detail when the article batch is empty.",
            }
        ]
    lead = articles[0]
    rules = [
        {
            "eyebrow": _signal_tag(lead),
            "title": f"Lead with {_source(lead)} because it scored {lead.score:.2f}.",
            "body": f"The matched terms are {_keyword_phrase(lead)}, which explains why this story outranks the rest of the queue.",
        }
    ]
    if len(articles) > 1:
        second = articles[1]
        rules.append(
            {
                "eyebrow": _label_for_category(second.category),
                "title": f"Keep {_source(second)} visible as the second read.",
                "body": f"It adds {_keyword_phrase(second)} and keeps the briefing from becoming a single-source summary.",
            }
        )
    if len(articles) > 2:
        third = articles[2]
        rules.append(
            {
                "eyebrow": "Decision",
                "title": f"Use {_signal_tag(third).lower()} framing for {_source(third)}.",
                "body": f"The article is {_freshness(third)} old and belongs in {_label_for_category(third.category).lower()}, so it should be read after the top two.",
            }
        )
    return rules[:3]


def _side_stack(articles: list[RankedArticle], top_categories: Counter[str]) -> list[dict[str, str | bool]]:
    lead = articles[0] if articles else None
    sources = _join_human([_source(article) for article in articles[:4]])
    category = top_categories.most_common(1)[0][0] if top_categories else "general_ai"
    source_count = len({_source(article) for article in articles})
    return [
        {
            "eyebrow": f"{_source(lead) if lead else 'No source'} cue",
            "title": _clip(lead.article.title, 96) if lead else "Waiting on today's lead article.",
            "body": (
                f"Score {lead.score:.2f}; matched {_keyword_phrase(lead)}; category {_label_for_category(lead.category).lower()}."
                if lead
                else "The side rail will fill from the highest-ranked article once inputs are available."
            ),
            "visual": True,
            "sparkline": False,
        },
        {
            "eyebrow": "Source mix",
            "title": f"{source_count} source{'s' if source_count != 1 else ''} in the lead set.",
            "body": f"Today's visible read comes from {sources or 'no ranked sources yet'}.",
            "visual": False,
            "sparkline": False,
        },
        {
            "eyebrow": "Signal shape",
            "title": f"{_label_for_category(category)} is the densest cluster.",
            "body": f"Tags come from score and category: {_join_human([_signal_tag(article) for article in articles[:3]]) or 'none yet'}.",
            "visual": False,
            "sparkline": True,
        },
    ]


def _footer_note(default_note: str, articles: list[RankedArticle]) -> str:
    if not articles:
        return default_note
    lead = articles[0]
    return (
        f"Archived with {_source(lead)} as the lead source, {_label_for_category(lead.category).lower()} as the top category, "
        f"and {_keyword_phrase(lead)} as the matched evidence."
    )


def _asset_label(articles: list[RankedArticle]) -> str:
    return f"{len(articles[:3])} story cues" if articles else "no story cues"


def _footrail_traits(top_categories: Counter[str]) -> str:
    if not top_categories:
        return "empty input / archived / html-first"
    return " / ".join(_label_for_category(category).lower() for category, _count in top_categories.most_common(3))


def _footrail_tags(articles: list[RankedArticle]) -> list[str]:
    tags = []
    for article in articles[:4]:
        tags.append(f"{_signal_tag(article).lower()} {article.score:.1f}")
    return tags or ["no ranked articles", "metadata kept", "html-first"]


def _source(article: RankedArticle) -> str:
    return article.article.source.strip() or "Unknown source"


def _possessive(text: str) -> str:
    return f"{text}'" if text.endswith("s") else f"{text}'s"


def _summary(article: RankedArticle, limit: int) -> str:
    text = article.article.description.strip() or article.article.content_text.strip()
    return _clip(text.rstrip(".") + "." if text else "", limit)


def _keyword_phrase(article: RankedArticle) -> str:
    if article.matched_keywords:
        return ", ".join(article.matched_keywords[:4])
    return _label_for_category(article.category).lower()


def _freshness(article: RankedArticle) -> str:
    if article.days_old < 0.05:
        return "under an hour"
    if article.days_old < 1:
        hours = max(1, round(article.days_old * 24))
        return f"{hours}h"
    return f"{article.days_old:.1f}d"


def _real_url(url: str) -> str | None:
    text = url.strip()
    if text.startswith(("https://", "http://")):
        return text
    return None


def _clip(text: str, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    clipped = normalized[: limit - 3].rsplit(" ", 1)[0].rstrip(".,;:")
    return f"{clipped}..."


def _join_human(items: list[str]) -> str:
    deduped = list(dict.fromkeys(item for item in items if item))
    if not deduped:
        return ""
    if len(deduped) == 1:
        return deduped[0]
    if len(deduped) == 2:
        return f"{deduped[0]} and {deduped[1]}"
    return f"{', '.join(deduped[:-1])}, and {deduped[-1]}"

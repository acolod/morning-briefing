from pathlib import Path

from briefing.build import _load_articles
from briefing.config import load_config
from briefing.gather import Article
from briefing.rank import rank
from briefing.render import render


def test_empty_articles_renders():
    config = load_config(Path("config.yaml"))

    html = render([], config)

    assert "<!DOCTYPE html>" in html
    assert len(html) > 500


def test_single_article_renders():
    config = load_config(Path("config.yaml"))
    articles = [
        Article(
            title="Hermes agents improve recovery loops",
            url="https://example.com/hermes-recovery",
            source="Example",
            description="Agent workflows improve tool reliability and recovery loops.",
            content_text="hermes agents tool use memory browser workflows reliability",
            date="2026-06-03T10:00:00+00:00",
        )
    ]

    html = render(rank(articles, config), config)

    assert "</html>" in html


def test_malformed_json_fallback(tmp_path):
    articles_path = tmp_path / "articles.json"
    articles_path.write_text("this is not json", encoding="utf-8")

    articles = _load_articles(articles_path)

    assert articles == []


def test_no_keyword_matches_ranks_general():
    config = load_config(Path("config.yaml"))
    articles = [
        Article(
            title="Cooking recipes for slow Sunday dinners",
            url="https://example.com/cooking-recipes",
            source="Example",
            description="A collection of kitchen notes and family dinner recipes.",
            content_text="soup simmer pantry herbs roast vegetables sourdough",
            date="2026-06-03T10:00:00+00:00",
        )
    ]

    ranked = rank(articles, config)

    assert ranked[0].category == "general_ai"


def test_render_uses_article_specific_editorial_sections():
    config = load_config(Path("config.yaml"))
    articles = [
        Article(
            title="Agent observability consoles expose retry storms before launch",
            url="https://example.com/agent-observability",
            source="Ops Ledger",
            description="New dashboards trace failed tool calls, stalled browser sessions, and memory misses before agent workflows reach production users.",
            content_text="agents observability retry tool calls browser workflows memory production reliability",
            date="2026-06-03T13:00:00+00:00",
        ),
        Article(
            title="Inference teams cut model spend with routing budgets",
            url="https://example.com/model-routing-budgets",
            source="Inference Report",
            description="Teams are routing requests by context size, latency target, and task value instead of sending every workload to the same frontier model.",
            content_text="models inference pricing latency context window routing deployment cost benchmarks",
            date="2026-06-03T12:00:00+00:00",
        ),
        Article(
            title="Product teams turn AI features into daily operator checklists",
            url="https://example.com/operator-checklists",
            source="Product Systems",
            description="AI products are performing better when the feature is attached to a repeated operator decision instead of a broad prompt box.",
            content_text="product building workflow shipping daily loop operator experiments design",
            date="2026-06-03T11:00:00+00:00",
        ),
    ]

    html = render(rank(articles, config), config)

    retired_template_phrases = [
        "Article-style visuals are the better fit here.",
        "Use at most one or two visuals in an issue.",
        "Article image mock slot",
        "Semantic color, not decorative color.",
        "Polished first, retro second.",
        "Hosted HTML artifact + Telegram link",
    ]
    for phrase in retired_template_phrases:
        assert phrase not in html

    assert 'href="#"' not in html
    assert "Ops Ledger" in html
    assert "retry" in html.lower()

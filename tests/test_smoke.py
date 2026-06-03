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

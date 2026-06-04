from pathlib import Path

from markupsafe import escape

from briefing.build import _DEMO_EDITORIAL, build
from briefing.config import load_config
from briefing.gather import Article
from briefing.rank import rank
from briefing.render import render


def test_empty_editorial_renders():
    config = load_config(Path("config.yaml"))

    html = render({"signals": [], "radar": []}, config=config)

    assert html.startswith("<!DOCTYPE html>")
    assert "No supporting signals in this issue." in html
    assert "Top story" in html
    assert "One move today" in html


def test_demo_editorial_renders():
    config = load_config(Path("config.yaml"))

    html = render(_DEMO_EDITORIAL, config=config)

    assert "</html>" in html
    assert "ADOPT" in html


def test_malformed_articles_file_fallback(tmp_path):
    articles_path = tmp_path / "articles.json"
    articles_path.write_text("this is not json", encoding="utf-8")

    html = build(articles_path=articles_path)

    assert str(escape(_DEMO_EDITORIAL["top_story"]["headline"])) in html


def test_build_with_article_compatibility():
    html = build(
        articles=[
            {
                "title": "Hermes agents improve recovery loops",
                "url": "https://example.com/hermes-recovery",
                "source": "Example",
                "description": "Agent workflows improve tool reliability and recovery loops.",
            }
        ]
    )

    assert "Hermes agents improve recovery loops" in html
    assert "https://example.com/hermes-recovery" in html


def test_rank_compatibility_without_ranking_config():
    ranked = rank(
        [
            Article(
                title="Hermes recovery loops",
                url="https://example.com/hermes",
                source="Example",
                description="Agent recovery loop note.",
                content_text="",
            )
        ],
        config=load_config(Path("config.yaml")),
    )

    assert len(ranked) == 1
    assert ranked[0].article.title == "Hermes recovery loops"

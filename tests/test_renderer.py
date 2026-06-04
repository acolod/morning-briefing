import copy
import json
import re
import subprocess
import sys

from markupsafe import escape

from briefing.build import _DEMO_EDITORIAL, build
from briefing.render import render
from briefing.verify_urls import verify_urls


RETIRED_PHRASES = [
    "Article-style visuals are the better fit here.",
    "Use at most one or two visuals in an issue.",
    "Article image mock slot",
    "Semantic color, not decorative color.",
    "Polished first, retro second.",
    "Hosted HTML artifact + Telegram link",
    "Make the first screen answer",
    "Momentum should rise quickly",
    "HTML carries the full reading surface",
    "The artifact is the product.",
]


def test_editorial_json_renders():
    html = render(copy.deepcopy(_DEMO_EDITORIAL))

    assert html.startswith("<!DOCTYPE html>")
    assert '<html lang="en">' in html
    assert "<section" in html
    assert "</html>" in html


def test_all_tags_render():
    html = render(copy.deepcopy(_DEMO_EDITORIAL))

    for tag in ("adopt", "try", "track", "note"):
        assert f"tag--{tag}" in html
        assert f">{tag.upper()}<" in html


def test_all_links_real():
    editorial = copy.deepcopy(_DEMO_EDITORIAL)
    editorial["signals"].append(
        {
            "headline": "Invalid signal URL should not render a placeholder href",
            "source": "Bad Source",
            "url": "#",
            "take": "Invalid links should be normalized before rendering.",
            "tag": "note",
        }
    )

    html = render(editorial)
    hrefs = re.findall(r'href="([^"]+)"', html)

    assert 'href="#"' not in html
    assert 'href=""' not in html
    assert hrefs
    assert all(href.startswith(("https://", "http://")) for href in hrefs)


def test_no_static_phrases():
    html = render(copy.deepcopy(_DEMO_EDITORIAL))

    for phrase in RETIRED_PHRASES:
        assert phrase not in html


def test_top_story_present():
    editorial = copy.deepcopy(_DEMO_EDITORIAL)
    html = render(editorial)

    assert str(escape(editorial["top_story"]["headline"])) in html
    assert str(escape(editorial["top_story"]["take"])) in html
    assert editorial["top_story"]["url"] in html


def test_radar_renders():
    editorial = copy.deepcopy(_DEMO_EDITORIAL)
    html = render(editorial)

    for item in editorial["radar"]:
        assert item in html


def test_one_move_renders():
    editorial = copy.deepcopy(_DEMO_EDITORIAL)
    html = render(editorial)

    assert editorial["one_move"] in html


def test_empty_editorial():
    editorial = copy.deepcopy(_DEMO_EDITORIAL)
    editorial["signals"] = []
    editorial["radar"] = []

    html = render(editorial)

    assert html.startswith("<!DOCTYPE html>")
    assert "No supporting signals in this issue." in html
    assert "Top story" in html
    assert "One move today" in html


def test_malformed_json(tmp_path, capsys):
    editorial_path = tmp_path / "editorial.json"
    editorial_path.write_text("this is not json", encoding="utf-8")

    html = build(editorial_json_path=editorial_path)
    captured = capsys.readouterr()

    assert "Warning: could not load editorial JSON" in captured.err
    assert str(escape(_DEMO_EDITORIAL["top_story"]["headline"])) in html


def test_issue_metadata():
    editorial = copy.deepcopy(_DEMO_EDITORIAL)
    html = render(editorial)

    assert "Issue metadata" in html
    assert editorial["issue"]["date"] in html
    assert editorial["issue"]["time"] in html
    assert f"{editorial['issue']['number']:03d}" in html
    assert str(editorial["issue"]["sources_scanned"]) in html
    assert str(editorial["issue"]["articles_read"]) in html


def test_demo_mode():
    result = subprocess.run(
        [sys.executable, "-m", "briefing.build", "--demo"],
        text=True,
        capture_output=True,
        check=True,
    )

    assert result.stdout.startswith("<!DOCTYPE html>")
    assert "Top story" in result.stdout
    assert "Signals" in result.stdout
    assert "Radar" in result.stdout
    assert "One move today" in result.stdout


def test_output_flag(tmp_path):
    output_path = tmp_path / "test.html"

    subprocess.run(
        [sys.executable, "-m", "briefing.build", "--demo", "--output", str(output_path)],
        text=True,
        capture_output=True,
        check=True,
    )

    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_editorial_json_cli(tmp_path):
    editorial_path = tmp_path / "editorial.json"
    editorial_path.write_text(json.dumps(_DEMO_EDITORIAL), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "briefing.build", "--editorial-json", str(editorial_path)],
        text=True,
        capture_output=True,
        check=True,
    )

    assert result.stdout.startswith("<!DOCTYPE html>")
    assert str(escape(_DEMO_EDITORIAL["top_story"]["headline"])) in result.stdout


def test_verify_urls_removes_dead(monkeypatch):
    editorial = copy.deepcopy(_DEMO_EDITORIAL)
    editorial["signals"] = [
        {
            "headline": "Live signal",
            "source": "Live Source",
            "url": "https://example.com/live",
            "take": "This should stay.",
            "tag": "try",
        },
        {
            "headline": "Dead signal",
            "source": "Dead Source",
            "url": "https://example.com/dead",
            "take": "This should be removed.",
            "tag": "track",
        },
    ]
    editorial["radar"] = [
        "Live radar item https://example.com/radar-live",
        "Dead radar item https://example.com/radar-dead",
    ]

    def fake_url_is_live(url: str, timeout: int = 5) -> tuple[bool, str | None]:
        if url.endswith("/dead") or url.endswith("/radar-dead"):
            return False, "404"
        return True, None

    monkeypatch.setattr("briefing.verify_urls._url_is_live", fake_url_is_live)

    verified = verify_urls(editorial)

    assert [item["headline"] for item in verified["signals"]] == ["Live signal"]
    assert verified["signals"][0]["verified"] is True
    assert verified["radar"] == ["Live radar item https://example.com/radar-live"]
    assert verified["verification_report"]["removed"] == [
        {"path": "signals[1].url", "url": "https://example.com/dead", "reason": "404"},
        {"path": "radar[1]", "url": "https://example.com/radar-dead", "reason": "404"},
    ]


def test_verify_urls_passes_good(monkeypatch):
    editorial = copy.deepcopy(_DEMO_EDITORIAL)

    def fake_url_is_live(url: str, timeout: int = 5) -> tuple[bool, str | None]:
        return True, None

    monkeypatch.setattr("briefing.verify_urls._url_is_live", fake_url_is_live)

    verified = verify_urls(editorial)

    assert len(verified["signals"]) == len(editorial["signals"])
    assert verified["top_story"]["verified"] is True
    assert all(signal["verified"] is True for signal in verified["signals"])
    assert verified["verification_report"]["removed"] == []

import json
from datetime import datetime, timedelta, timezone

from briefing.sources.fetchers import SourceItem
from briefing.sources.pool import SourcePool
from briefing.sources.validate import ValidationGate, ValidationReport


def _item(
    title: str = "Hermes agent protocol update",
    url: str = "https://example.com/hermes",
    source_name: str = "Example",
    source_type: str = "rss",
    published: str | None = None,
    description: str | None = "Useful agent protocol context.",
) -> SourceItem:
    return SourceItem.create(
        title=title,
        url=url,
        source_name=source_name,
        source_type=source_type,
        published=published,
        description=description,
    )


def test_source_item_creation():
    item = _item()

    assert item.title == "Hermes agent protocol update"
    assert item.url == "https://example.com/hermes"
    assert item.source_name == "Example"
    assert item.source_type == "rss"
    assert len(item.content_hash) == 64


def test_dedup_by_hash():
    item = _item()
    duplicate = SourceItem(
        title="Different title",
        url="https://example.com/other",
        source_name="Other",
        source_type="rss",
        published=None,
        description=None,
        content_hash=item.content_hash,
    )

    deduped = SourcePool().deduplicate([item, duplicate])

    assert deduped == [item]


def test_reject_stale():
    fresh = _item(published=datetime.now(timezone.utc).isoformat())
    old = _item(
        title="Old item",
        url="https://example.com/old",
        published=(datetime.now(timezone.utc) - timedelta(hours=72)).isoformat(),
    )
    undated = _item(title="Undated item", url="https://example.com/undated", published=None)

    kept = SourcePool().reject_stale([fresh, old, undated], max_age_hours=48)

    assert fresh in kept
    assert undated in kept
    assert old not in kept


def test_validation_gate_urls(monkeypatch):
    live = _item(url="https://example.com/live")
    dead = _item(title="Dead item", url="https://example.com/dead")

    def fake_url_is_live(url: str, timeout: int) -> tuple[bool, str | None]:
        if url.endswith("/dead"):
            return False, "404"
        return True, None

    gate = ValidationGate()
    monkeypatch.setattr(gate, "_url_is_live", fake_url_is_live)

    checked = gate.check_urls([live, dead])

    assert checked == [live]
    assert gate.failed_urls == [("https://example.com/dead", "404")]


def test_validation_report():
    report = ValidationReport(
        total_input=10,
        removed_stale=2,
        removed_dead_urls=1,
        removed_duplicates=3,
        removed_blocked_domains=1,
        passed=3,
        failed_urls=[("https://example.com/dead", "404")],
    )

    assert report.total_input == 10
    assert report.passed == 3
    assert report.failed_urls == [("https://example.com/dead", "404")]


def test_filter_by_keywords():
    hermes = _item(description="MCP dynamic discovery for agent tools.")
    unrelated = _item(
        title="GPU earnings recap",
        url="https://example.com/gpu",
        description="Quarterly chip sales.",
    )

    filtered = SourcePool().filter_by_keywords([hermes, unrelated], ["mcp", "agents"])

    assert filtered == [hermes]


def test_pool_roundtrip():
    item = _item()
    payload = SourcePool().to_json([item])
    parsed = json.loads(payload)

    assert parsed == [
        {
            "title": item.title,
            "url": item.url,
            "source_name": item.source_name,
            "source_type": item.source_type,
            "published": item.published,
            "description": item.description,
            "content_hash": item.content_hash,
        }
    ]
    assert SourcePool.from_json(payload) == [item]


def test_blocked_domains():
    good = _item(url="https://example.com/good")
    spam = _item(title="Spam", url="https://spam.example/bad")

    kept = ValidationGate().check_source_reputation([good, spam], ["spam.example"])

    assert kept == [good]

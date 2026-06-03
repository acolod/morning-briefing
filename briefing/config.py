from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class RenderConfig:
    timezone: str = "America/Los_Angeles"
    issue_prefix: str = "Issue"
    title: str = "Morning AI Brief"
    footer_note: str = "Rendered from editorial JSON."
    version: str = "v2 editorial"


@dataclass(frozen=True)
class BriefingConfig:
    render: RenderConfig


def load_config(path: str | Path = "config.yaml") -> BriefingConfig:
    config_path = Path(path)
    if config_path.exists():
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    else:
        raw = {}
    render_raw = raw.get("render", {}) if isinstance(raw, dict) else {}
    render = RenderConfig(
        timezone=str(render_raw.get("timezone", RenderConfig.timezone)),
        issue_prefix=str(render_raw.get("issue_prefix", RenderConfig.issue_prefix)),
        title=str(render_raw.get("title", RenderConfig.title)),
        footer_note=str(render_raw.get("footer_note", RenderConfig.footer_note)),
        version=str(render_raw.get("version", RenderConfig.version)),
    )
    return BriefingConfig(render=render)


def load_momentum(path: str | Path | None) -> dict[str, float]:
    """Compatibility helper for older callers; momentum is no longer used."""
    if path is None:
        return {}
    momentum_path = Path(path)
    if not momentum_path.exists():
        return {}
    try:
        raw = json.loads(momentum_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return {}
    if isinstance(raw, dict) and "topics" in raw:
        raw = raw["topics"]
    if not isinstance(raw, dict):
        return {}
    result: dict[str, float] = {}
    for key, value in raw.items():
        try:
            result[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return result


def category_names(config: BriefingConfig) -> tuple[str, ...]:
    return ()


def category_keywords(config: BriefingConfig) -> dict[str, tuple[str, ...]]:
    return {}


def category_weights(config: BriefingConfig) -> dict[str, float]:
    return {}

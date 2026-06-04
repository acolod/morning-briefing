from __future__ import annotations

import copy
import re
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


USER_AGENT = "morning-briefing/0.1 (+https://example.com)"
URL_RE = re.compile(r"https?://[^\s<>'\")]+")


def verify_urls(editorial: dict, timeout: int = 5) -> dict:
    """Return editorial JSON with dead signal/radar URLs removed and verified flags set."""
    cleaned = copy.deepcopy(editorial)
    removed: list[dict[str, str]] = []

    top_story = _mapping(cleaned.get("top_story"))
    cleaned["top_story"] = top_story
    top_url = _text(top_story.get("url"))
    if top_url:
        is_live, reason = _url_is_live(top_url, timeout=timeout)
        top_story["verified"] = is_live
        if not is_live:
            top_story["url"] = ""
            removed.append({"path": "top_story.url", "url": top_url, "reason": reason or "unreachable"})

    kept_signals: list[dict[str, Any]] = []
    for index, signal in enumerate(_list(cleaned.get("signals"))):
        item = dict(signal) if isinstance(signal, Mapping) else {}
        url = _text(item.get("url"))
        if not url:
            item["verified"] = False
            kept_signals.append(item)
            continue
        is_live, reason = _url_is_live(url, timeout=timeout)
        item["verified"] = is_live
        if is_live:
            kept_signals.append(item)
        else:
            removed.append({"path": f"signals[{index}].url", "url": url, "reason": reason or "unreachable"})
    cleaned["signals"] = kept_signals

    kept_radar: list[Any] = []
    for index, item in enumerate(_list(cleaned.get("radar"))):
        urls = _extract_urls(item)
        dead = []
        for url in urls:
            is_live, reason = _url_is_live(url, timeout=timeout)
            if not is_live:
                dead.append((url, reason or "unreachable"))
        if dead:
            for url, reason in dead:
                removed.append({"path": f"radar[{index}]", "url": url, "reason": reason})
        else:
            kept_radar.append(item)
    cleaned["radar"] = kept_radar

    cleaned["verification_report"] = {"removed": removed}
    return cleaned


def _url_is_live(url: str, timeout: int = 5) -> tuple[bool, str | None]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False, "invalid URL"
    try:
        request = Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=timeout) as response:
            if 200 <= response.status < 400:
                return True, None
            return False, str(response.status)
    except HTTPError as exc:
        return False, str(exc.code)
    except (TimeoutError, URLError, OSError) as exc:
        return False, exc.__class__.__name__


def _extract_urls(value: Any) -> list[str]:
    return URL_RE.findall(_text(value))


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""

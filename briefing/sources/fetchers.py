from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse
from urllib.request import Request, urlopen

RSS_FEEDS: tuple[tuple[str, str], ...] = (
    ("Hacker News", "https://hnrss.org/frontpage"),
    ("ArXiv AI", "http://export.arxiv.org/rss/cs.AI"),
    ("ArXiv ML", "http://export.arxiv.org/rss/cs.LG"),
    ("Anthropic Blog", "https://www.anthropic.com/feed.xml"),
    ("Google AI Blog", "https://blog.google/technology/ai/rss/"),
    ("Meta AI", "https://ai.meta.com/blog/rss/"),
    ("The Verge AI", "https://www.theverge.com/ai-artificial-intelligence/rss.xml"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
)


USER_AGENT = "morning-briefing/0.1 (+https://localhost)"


@dataclass(frozen=True)
class SourceItem:
    title: str
    url: str
    source_name: str
    source_type: str
    published: str | None
    description: str | None
    content_hash: str

    @classmethod
    def create(
        cls,
        title: str,
        url: str,
        source_name: str,
        source_type: str,
        published: str | None = None,
        description: str | None = None,
    ) -> "SourceItem":
        clean_title = _clean_text(title)
        clean_url = _normalize_url(url)
        digest = hashlib.sha256(f"{clean_title}|{clean_url}".encode("utf-8")).hexdigest()
        return cls(
            title=clean_title,
            url=clean_url,
            source_name=_clean_text(source_name),
            source_type=_clean_text(source_type).lower(),
            published=_normalize_date(published),
            description=_clean_text(description) or None,
            content_hash=digest,
        )


def fetch_sources(fetchers: list[str] | None = None, search_query: str | None = None) -> list[SourceItem]:
    selected = {fetcher.strip().lower() for fetcher in (fetchers or ["rss"]) if fetcher.strip()}
    items: list[SourceItem] = []
    if "rss" in selected:
        items.extend(fetch_rss_sources())
    if "web" in selected:
        items.extend(fetch_github_trending())
        if search_query:
            items.extend(fetch_duckduckgo_lite(search_query))
    return items


def fetch_rss_sources(feeds: tuple[tuple[str, str], ...] = RSS_FEEDS) -> list[SourceItem]:
    import feedparser

    items: list[SourceItem] = []
    for source_name, feed_url in feeds:
        parsed = feedparser.parse(feed_url, request_headers={"User-Agent": USER_AGENT})
        for entry in parsed.entries:
            title = entry.get("title") or ""
            url = entry.get("link") or ""
            if not title or not url:
                continue
            published = _entry_date(entry)
            description = entry.get("summary") or entry.get("description")
            items.append(
                SourceItem.create(
                    title=title,
                    url=url,
                    source_name=source_name,
                    source_type="rss",
                    published=published,
                    description=description,
                )
            )
    return items


def fetch_github_trending(language: str = "", since: str = "daily") -> list[SourceItem]:
    path = f"/trending/{quote_plus(language)}" if language else "/trending"
    url = f"https://github.com{path}?since={quote_plus(since)}"
    try:
        html_text = _fetch_text(url)
    except OSError:
        return []

    articles = re.findall(r"<article\b.*?</article>", html_text, flags=re.IGNORECASE | re.DOTALL)
    items: list[SourceItem] = []
    for article in articles:
        href_match = re.search(r'<h2[^>]*>.*?<a[^>]+href="([^"]+)"', article, flags=re.DOTALL)
        if not href_match:
            continue
        repo_path = html.unescape(href_match.group(1)).strip()
        repo_name = repo_path.strip("/").replace("/", " / ")
        desc_match = re.search(r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>(.*?)</p>', article, flags=re.DOTALL)
        description = _strip_tags(desc_match.group(1)) if desc_match else None
        items.append(
            SourceItem.create(
                title=repo_name,
                url=urljoin("https://github.com", repo_path),
                source_name="GitHub Trending",
                source_type="web",
                published=datetime.now(timezone.utc).isoformat(),
                description=description,
            )
        )
    return items


def fetch_duckduckgo_lite(query: str, max_results: int = 10) -> list[SourceItem]:
    search_url = f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"
    try:
        html_text = _fetch_text(search_url)
    except OSError:
        return []

    items: list[SourceItem] = []
    links = re.findall(r'<a[^>]+class="result-link"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html_text, flags=re.DOTALL)
    for raw_url, raw_title in links[:max_results]:
        url = _duckduckgo_result_url(html.unescape(raw_url))
        title = _strip_tags(raw_title)
        if title and url:
            items.append(
                SourceItem.create(
                    title=title,
                    url=url,
                    source_name="DuckDuckGo Lite",
                    source_type="web",
                    published=datetime.now(timezone.utc).isoformat(),
                    description=None,
                )
            )
    return items


def _fetch_text(url: str, timeout: int = 15) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _entry_date(entry: Any) -> str | None:
    for key in ("published", "updated", "created"):
        if entry.get(key):
            return _normalize_date(entry.get(key))
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return datetime(*value[:6], tzinfo=timezone.utc).isoformat()
    return None


def _normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _normalize_url(url: str) -> str:
    clean_url = html.unescape(str(url or "").strip())
    if clean_url.startswith("//"):
        return f"https:{clean_url}"
    if clean_url and not urlparse(clean_url).scheme:
        return f"https://{clean_url.lstrip('/')}"
    return clean_url


def _clean_text(value: str | None) -> str:
    text = _strip_tags(value or "")
    return re.sub(r"\s+", " ", text).strip()


def _strip_tags(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", str(value))).strip()


def _duckduckgo_result_url(url: str) -> str:
    parsed = urlparse(url)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        return unquote(target)
    return url

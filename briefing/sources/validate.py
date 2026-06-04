from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .fetchers import SourceItem, USER_AGENT
from .pool import SourcePool


DEFAULT_BLOCKED_DOMAINS = [
    "medium.com",
    "substack.com",
]


@dataclass(frozen=True)
class ValidationReport:
    total_input: int
    removed_stale: int
    removed_dead_urls: int
    removed_duplicates: int
    removed_blocked_domains: int
    passed: int
    failed_urls: list[tuple[str, str]]


class ValidationGate:
    def __init__(self, blocked_domains: list[str] | None = None) -> None:
        self.blocked_domains = blocked_domains if blocked_domains is not None else DEFAULT_BLOCKED_DOMAINS
        self.failed_urls: list[tuple[str, str]] = []

    def check_urls(self, items: list[SourceItem], timeout: int = 5) -> list[SourceItem]:
        self.failed_urls = []
        live: list[SourceItem] = []
        with ThreadPoolExecutor(max_workers=min(12, max(1, len(items)))) as executor:
            checks = list(executor.map(lambda item: self._url_is_live(item.url, timeout), items))
        for item, (is_live, reason) in zip(items, checks):
            if is_live:
                live.append(item)
            else:
                self.failed_urls.append((item.url, reason or "unreachable"))
        return live

    def check_freshness(self, items: list[SourceItem], max_hours: int = 48) -> list[SourceItem]:
        return SourcePool().reject_stale(items, max_age_hours=max_hours)

    def check_duplicates(self, items: list[SourceItem]) -> list[SourceItem]:
        return SourcePool().deduplicate(items)

    def check_source_reputation(
        self,
        items: list[SourceItem],
        blocked_domains: list[str] | None = None,
    ) -> list[SourceItem]:
        source_domains = blocked_domains if blocked_domains is not None else self.blocked_domains
        blocked = [domain.casefold() for domain in source_domains]
        kept: list[SourceItem] = []
        for item in items:
            domain = urlparse(item.url).netloc.casefold()
            if any(domain == blocked_domain or domain.endswith(f".{blocked_domain}") for blocked_domain in blocked):
                continue
            kept.append(item)
        return kept

    def run_all(
        self,
        items: list[SourceItem],
        max_hours: int = 48,
        timeout: int = 5,
    ) -> tuple[list[SourceItem], ValidationReport]:
        total_input = len(items)

        fresh = self.check_freshness(items, max_hours=max_hours)
        unique = self.check_duplicates(fresh)
        reputable = self.check_source_reputation(unique)
        live = self.check_urls(reputable, timeout=timeout)

        report = ValidationReport(
            total_input=total_input,
            removed_stale=total_input - len(fresh),
            removed_duplicates=len(fresh) - len(unique),
            removed_blocked_domains=len(unique) - len(reputable),
            removed_dead_urls=len(reputable) - len(live),
            passed=len(live),
            failed_urls=list(self.failed_urls),
        )
        return live, report

    def _url_is_live(self, url: str, timeout: int) -> tuple[bool, str | None]:
        if not urlparse(url).scheme:
            return False, "missing scheme"
        for method in ("HEAD", "GET"):
            try:
                request = Request(url, method=method, headers={"User-Agent": USER_AGENT})
                with urlopen(request, timeout=timeout) as response:
                    if 200 <= response.status < 400:
                        return True, None
                    return False, str(response.status)
            except HTTPError as exc:
                if exc.code in {403, 405, 429}:
                    return True, None
                if method == "HEAD" and exc.code in {400, 404, 500, 501}:
                    continue
                return False, str(exc.code)
            except (TimeoutError, URLError, OSError) as exc:
                if method == "HEAD":
                    continue
                return False, exc.__class__.__name__
        return False, "unreachable"

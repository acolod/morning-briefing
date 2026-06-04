from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .sources.pool import SourcePool
from .sources.validate import ValidationGate, ValidationReport


def run_pipeline(fetchers: list[str], max_age: int = 48, validate_urls: bool = True) -> dict[str, object]:
    pool = SourcePool()
    raw_items = asyncio.run(pool.fetch_all(fetchers))
    normalized = pool.normalize(raw_items)
    sorted_items = pool.sort_by_freshness(normalized)

    gate = ValidationGate()
    if validate_urls:
        validated, report = gate.run_all(sorted_items, max_hours=max_age)
    else:
        fresh = gate.check_freshness(sorted_items, max_hours=max_age)
        unique = gate.check_duplicates(fresh)
        reputable = gate.check_source_reputation(unique)
        validated = reputable
        report = ValidationReport(
            total_input=len(sorted_items),
            removed_stale=len(sorted_items) - len(fresh),
            removed_duplicates=len(fresh) - len(unique),
            removed_blocked_domains=len(unique) - len(reputable),
            removed_dead_urls=0,
            passed=len(validated),
            failed_urls=[],
        )

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "fetchers_run": fetchers,
        "source_count": len(validated),
        "validation": asdict(report),
        "sources": [
            {
                "title": item.title,
                "url": item.url,
                "source_name": item.source_name,
                "source_type": item.source_type,
                "published": item.published,
                "description": item.description,
                "content_hash": item.content_hash,
            }
            for item in validated
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gather and validate Morning AI Brief source candidates.")
    parser.add_argument("--fetchers", default="rss", help="Comma-separated fetchers to run: rss,web.")
    parser.add_argument("--max-age", type=int, default=48, help="Reject dated sources older than this many hours.")
    parser.add_argument("--output", type=str, default=None, help="Write validated source JSON to FILE.")
    parser.add_argument("--skip-url-validation", action="store_true", help="Skip live URL checks.")
    args = parser.parse_args(argv)

    fetchers = [fetcher.strip() for fetcher in args.fetchers.split(",") if fetcher.strip()]
    payload = run_pipeline(
        fetchers=fetchers or ["rss"],
        max_age=args.max_age,
        validate_urls=not args.skip_url_validation,
    )
    encoded = json.dumps(payload, indent=2)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(encoded + "\n", encoding="utf-8")
        print(
            f"Validated {payload['source_count']} sources from {', '.join(fetchers or ['rss'])}; wrote {output_path}",
            file=sys.stdout,
        )
    else:
        validation = payload["validation"]
        assert isinstance(validation, dict)
        print(
            "Validated "
            f"{payload['source_count']} sources from {', '.join(fetchers or ['rss'])} "
            f"({validation['total_input']} input, {validation['removed_stale']} stale, "
            f"{validation['removed_duplicates']} duplicates, {validation['removed_dead_urls']} dead URLs)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

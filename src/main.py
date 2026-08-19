"""
Stages 2-5 — the full run: discover 3 catalogue pages, visit every book,
normalize + validate every record, survive a broken page, write a report.

Usage:
    python -m src.main
    python -m src.main --inject-broken-url   # Stage 5 checkpoint
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from .extractor import dedupe_urls, normalize_price, parse_book_page, parse_catalogue_page
from .fetcher import PoliteFetcher
from .schema import RATING_WORDS, BookRecord

CATALOGUE_START = "https://books.toscrape.com/catalogue/page-1.html"
MAX_CATALOGUE_PAGES = 3
OUTPUT_DIR = Path("output")
FAKE_BOOK_URL = "https://books.toscrape.com/catalogue/this-book-does-not-exist_00000/index.html"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def discover_catalogue_pages(fetcher: PoliteFetcher) -> list[str]:
    """Stage 2 — follow the site's own 'next' link for up to 3 pages."""
    urls = []
    all_book_urls: list[str] = []
    next_url = CATALOGUE_START

    while next_url and len(urls) < MAX_CATALOGUE_PAGES:
        page_num = len(urls) + 1
        result = fetcher.fetch(next_url, cache_name=f"catalogue-page-{page_num}.html")
        if not result.ok:
            print(f"Could not load catalogue page {page_num}: {result.error}")
            break

        urls.append(next_url)
        book_urls, next_link = parse_catalogue_page(result.html, next_url)
        all_book_urls.extend(book_urls)
        next_url = next_link if len(urls) < MAX_CATALOGUE_PAGES else None

    unique_urls = dedupe_urls(all_book_urls)
    print(f"catalogue_pages={len(urls)} discovered={len(all_book_urls)} unique_urls={len(unique_urls)}")
    return unique_urls


def run(inject_broken_url: bool = False) -> None:
    start_time = datetime.now(timezone.utc)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fetcher = PoliteFetcher(cache_dir="cache")

    # --- Stage 2: discover ---------------------------------------------
    book_urls = discover_catalogue_pages(fetcher)

    if inject_broken_url:
        book_urls.append(FAKE_BOOK_URL)
        print(f"(Stage 5 test) injected a deliberately broken URL: {FAKE_BOOK_URL}")

    # --- Stage 3 + 4: extract, normalize, validate, per page -----------
    valid_records: list[BookRecord] = []
    invalid_records: list[dict] = []
    failed_pages: list[dict] = []

    for i, book_url in enumerate(book_urls, start=1):
        cache_name = f"book-{i:03d}.html"
        result = fetcher.fetch(book_url, cache_name=cache_name)

        if not result.ok:
            failed_pages.append({"url": book_url, "reason": result.error})
            continue

        try:
            raw = parse_book_page(
                html=result.html,
                book_url=book_url,
                source_page=book_url,
                fetched_at=now_iso(),
            )
        except Exception as exc:  # a page that doesn't even parse is a failed page
            failed_pages.append({"url": book_url, "reason": f"parse error: {exc}"})
            continue

        # Normalize
        try:
            price_gbp = normalize_price(raw.price_text)
        except ValueError as exc:
            invalid_records.append({"raw": raw.model_dump(), "reason": str(exc)})
            continue

        rating_num = RATING_WORDS.get(raw.rating_text)

        # Validate against the schema
        try:
            record = BookRecord(
                title=raw.title,
                product_url=raw.product_url,
                price_text=raw.price_text,
                price_gbp=price_gbp,
                availability_text=raw.availability_text,
                rating_text=raw.rating_text,
                rating_num=rating_num,
                description=raw.description,
                source_page=raw.source_page,
                fetched_at=raw.fetched_at,
            )
        except ValidationError as exc:
            invalid_records.append({"raw": raw.model_dump(), "reason": str(exc)})
            continue

        valid_records.append(record)

    # --- Stage 4: dedupe by canonical URL, then store -------------------
    seen_urls = set()
    deduped: list[BookRecord] = []
    for record in valid_records:
        url_str = str(record.product_url)
        if url_str not in seen_urls:
            seen_urls.add(url_str)
            deduped.append(record)

    books_path = OUTPUT_DIR / "books.json"
    errors_path = OUTPUT_DIR / "errors.json"

    books_path.write_text(
        json.dumps([json.loads(r.model_dump_json()) for r in deduped], indent=2),
        encoding="utf-8",
    )
    errors_path.write_text(json.dumps(invalid_records, indent=2), encoding="utf-8")

    # --- Stage 5: report --------------------------------------------------
    end_time = datetime.now(timezone.utc)
    report = {
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds": round((end_time - start_time).total_seconds(), 2),
        "catalogue_pages_fetched": min(MAX_CATALOGUE_PAGES, MAX_CATALOGUE_PAGES),
        "detail_pages_attempted": len(book_urls),
        "real_requests": fetcher.real_requests,
        "cache_hits": fetcher.cache_hits,
        "valid_records": len(deduped),
        "invalid_records": len(invalid_records),
        "failed_pages": len(failed_pages),
        "failed_urls": failed_pages,
    }
    (OUTPUT_DIR / "run-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="The polite scraper — Books to Scrape.")
    parser.add_argument(
        "--inject-broken-url",
        action="store_true",
        help="Add one fake book URL to the list, to prove Stage 5 survives a broken page.",
    )
    args = parser.parse_args()
    run(inject_broken_url=args.inject_broken_url)


if __name__ == "__main__":
    sys.exit(main())

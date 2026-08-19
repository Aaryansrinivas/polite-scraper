"""
Parser tests — run entirely against saved fixtures, no network needed.
    python -m pytest tests/ -v
"""

from pathlib import Path

import pytest

from src.extractor import dedupe_urls, normalize_price, parse_book_page, parse_catalogue_page

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# 1. Price normalization -----------------------------------------------
def test_normalize_price_strips_currency_symbol():
    assert normalize_price("£51.77") == 51.77


def test_normalize_price_raises_when_no_number_present():
    with pytest.raises(ValueError):
        normalize_price("Price unavailable")


# 2. Relative -> absolute URL conversion --------------------------------
def test_catalogue_relative_links_become_absolute():
    html = load("catalogue_page.html")
    book_urls, next_url = parse_catalogue_page(html, "https://books.toscrape.com/catalogue/page-1.html")
    assert all(u.startswith("https://books.toscrape.com/") for u in book_urls)
    assert next_url == "https://books.toscrape.com/catalogue/page-2.html"


# 3. Missing description handled as null, not invented -----------------
def test_missing_description_is_none():
    html = load("book_no_description.html")
    record = parse_book_page(
        html, "https://books.toscrape.com/catalogue/no-description-book_1/index.html",
        source_page="https://books.toscrape.com/catalogue/page-1.html",
        fetched_at="2026-01-01T00:00:00Z",
    )
    assert record.description is None


# 4. Duplicate URL removal ----------------------------------------------
def test_dedupe_urls_keeps_first_seen_order():
    urls = ["a", "b", "a", "c", "b"]
    assert dedupe_urls(urls) == ["a", "b", "c"]


# 5. Malformed fixture — parser degrades instead of crashing ------------
def test_malformed_page_does_not_crash_and_flags_missing_price():
    html = load("book_malformed.html")
    record = parse_book_page(
        html, "https://books.toscrape.com/catalogue/broken_1/index.html",
        source_page="https://books.toscrape.com/catalogue/page-1.html",
        fetched_at="2026-01-01T00:00:00Z",
    )
    assert record.title.startswith("Broken Page Book")
    assert record.price_text == ""  # no price on the page — caught later by normalize/validate
    with pytest.raises(ValueError):
        normalize_price(record.price_text)


# 6. Bonus: a normal page extracts all eight fields ----------------------
def test_normal_page_extracts_all_fields():
    html = load("book_normal.html")
    record = parse_book_page(
        html, "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        source_page="https://books.toscrape.com/catalogue/page-1.html",
        fetched_at="2026-01-01T00:00:00Z",
    )
    assert record.title == "A Light in the Attic"
    assert record.price_text == "£51.77"
    assert "In stock" in record.availability_text
    assert record.rating_text == "Three"
    assert record.description is not None
    assert record.product_url.startswith("https://")

"""
Stage 2 & Stage 3 — turn HTML into raw fields.

Selectors are aimed at the product area of the page (product_pod,
product_main), not "the first thing that looks like a price".
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .schema import RATING_WORDS, RawRecord


def parse_catalogue_page(html: str, page_url: str) -> Tuple[List[str], Optional[str]]:
    """
    Stage 2. Returns (absolute book urls on this page, absolute url of the
    'next' page, or None if this is the last of the three).
    """
    soup = BeautifulSoup(html, "lxml")

    book_urls = []
    for pod in soup.select("article.product_pod"):
        link = pod.select_one("h3 a")
        if link and link.get("href"):
            book_urls.append(urljoin(page_url, link["href"]))

    next_url = None
    next_link = soup.select_one("li.next a")
    if next_link and next_link.get("href"):
        next_url = urljoin(page_url, next_link["href"])

    return book_urls, next_url


def parse_book_page(html: str, book_url: str, source_page: str, fetched_at: str) -> RawRecord:
    """Stage 3. Extract the eight raw fields for one book."""
    soup = BeautifulSoup(html, "lxml")

    main = soup.select_one("div.product_main") or soup

    title_tag = main.select_one("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    price_tag = main.select_one("p.price_color")
    price_text = price_tag.get_text(strip=True) if price_tag else ""

    availability_tag = main.select_one("p.instock.availability")
    availability_text = (
        " ".join(availability_tag.get_text(strip=True).split()) if availability_tag else ""
    )

    rating_tag = main.select_one("p.star-rating")
    rating_text = "Unknown"
    if rating_tag:
        classes = rating_tag.get("class", [])
        for cls in classes:
            if cls in RATING_WORDS:
                rating_text = cls
                break

    # Canonical URL: prefer the page's own <link rel="canonical">, since
    # that is the address the site itself calls authoritative.
    canonical_tag = soup.select_one('link[rel="canonical"]')
    product_url = urljoin(book_url, canonical_tag["href"]) if canonical_tag and canonical_tag.get("href") else book_url

    # Some books have no description at all — store null, never invent text.
    description = None
    desc_heading = soup.select_one("#product_description")
    if desc_heading:
        desc_p = desc_heading.find_next_sibling("p")
        if desc_p:
            text = desc_p.get_text(strip=True)
            description = text or None

    return RawRecord(
        title=title,
        product_url=product_url,
        price_text=price_text,
        availability_text=availability_text or "Unknown",
        rating_text=rating_text,
        description=description,
        source_page=source_page,
        fetched_at=fetched_at,
    )


PRICE_RE = re.compile(r"(\d+(?:\.\d+)?)")


def normalize_price(price_text: str) -> float:
    """'£51.77' -> 51.77. Raises ValueError if no number is found."""
    match = PRICE_RE.search(price_text)
    if not match:
        raise ValueError(f"no numeric price found in {price_text!r}")
    return float(match.group(1))


def dedupe_urls(urls: List[str]) -> List[str]:
    """Stage 2 — remove duplicate links, keep first-seen order."""
    seen = set()
    result = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            result.append(u)
    return result

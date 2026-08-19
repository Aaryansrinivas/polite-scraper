"""
Stage 1 & Stage 5 — fetch once, cache once, and don't die on a bad page.

Politeness rules baked in here so every caller gets them for free:
  - an honest user-agent that names us
  - a timeout, so a request can never hang forever
  - a status-code check before anything is treated as real HTML
  - a saved copy on disk (cache/) so re-running the script during
    development never re-asks the live site
  - a small delay between REAL requests only (cache hits are free)
  - one retry, with backoff, for timeouts and 5xx — never for 404/403
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/YOUR_USERNAME/YOUR_REPO)"
TIMEOUT_SECONDS = 10
POLITE_DELAY_SECONDS = 0.6
RETRY_BACKOFF_SECONDS = 2


@dataclass
class FetchResult:
    url: str
    html: Optional[str]
    status_code: Optional[int]
    from_cache: bool
    ok: bool
    error: Optional[str] = None


def _cache_path_for(url: str, cache_dir: Path) -> Path:
    """Turn a URL into a stable, readable-ish cache filename."""
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    slug = url.rstrip("/").split("/")[-1] or "index"
    slug = "".join(c if c.isalnum() or c in ("-", "_", ".") else "-" for c in slug)
    return cache_dir / f"{slug}-{digest}.html"


class PoliteFetcher:
    def __init__(self, cache_dir: str = "cache", session: Optional[requests.Session] = None):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

        # Counters for the run report (Stage 5).
        self.real_requests = 0
        self.cache_hits = 0

    def fetch(self, url: str, cache_name: Optional[str] = None) -> FetchResult:
        """
        Fetch a URL politely, using the on-disk cache when available.
        cache_name lets a caller pin a specific cache filename
        (e.g. cache/catalogue-page-1.html) instead of the hashed default.
        """
        cache_path = (
            self.cache_dir / cache_name if cache_name else _cache_path_for(url, self.cache_dir)
        )

        if cache_path.exists():
            self.cache_hits += 1
            html = cache_path.read_text(encoding="utf-8")
            print(f"CACHE HIT  {url}  ({len(html)} bytes)")
            return FetchResult(url=url, html=html, status_code=200, from_cache=True, ok=True)

        return self._fetch_live(url, cache_path)

    def _fetch_live(self, url: str, cache_path: Path, attempt: int = 1) -> FetchResult:
        try:
            response = self.session.get(url, timeout=TIMEOUT_SECONDS)
        except requests.exceptions.Timeout:
            if attempt == 1:
                print(f"TIMEOUT    {url}  (retrying once)")
                time.sleep(RETRY_BACKOFF_SECONDS)
                return self._fetch_live(url, cache_path, attempt=2)
            return FetchResult(
                url=url, html=None, status_code=None, from_cache=False, ok=False,
                error="timeout after retry",
            )
        except requests.exceptions.RequestException as exc:
            return FetchResult(
                url=url, html=None, status_code=None, from_cache=False, ok=False,
                error=f"connection error: {exc}",
            )

        self.real_requests += 1
        status = response.status_code

        if status == 200:
            cache_path.write_text(response.text, encoding="utf-8")
            print(f"FETCH      {url}  ({len(response.text)} bytes, status {status})")
            time.sleep(POLITE_DELAY_SECONDS)
            return FetchResult(url=url, html=response.text, status_code=status, from_cache=False, ok=True)

        if status in (404, 403):
            # Do not retry: 404 won't appear on a second ask, 403 means "no".
            print(f"FAILED     {url}  (status {status}, not retrying)")
            time.sleep(POLITE_DELAY_SECONDS)
            return FetchResult(
                url=url, html=None, status_code=status, from_cache=False, ok=False,
                error=f"HTTP {status}",
            )

        if status >= 500 and attempt == 1:
            print(f"SERVER ERR {url}  (status {status}, retrying once)")
            time.sleep(RETRY_BACKOFF_SECONDS)
            return self._fetch_live(url, cache_path, attempt=2)

        print(f"FAILED     {url}  (status {status})")
        time.sleep(POLITE_DELAY_SECONDS)
        return FetchResult(
            url=url, html=None, status_code=status, from_cache=False, ok=False,
            error=f"HTTP {status}",
        )

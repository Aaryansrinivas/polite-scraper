"""
Stage 0 — check before you collect.

Fetches robots.txt once and prints what it found. Run this once, by
hand, and paste the result into README.md's "Target classification"
section. It does not touch the cache or output pipeline.
"""

import requests

from .fetcher import USER_AGENT

ROBOTS_URL = "https://books.toscrape.com/robots.txt"


def main() -> None:
    print(f"Requesting {ROBOTS_URL} once, as {USER_AGENT!r} ...")
    try:
        response = requests.get(ROBOTS_URL, headers={"User-Agent": USER_AGENT}, timeout=10)
    except requests.exceptions.RequestException as exc:
        print(f"Request failed: {exc}")
        return

    if response.status_code == 200:
        print(f"robots.txt found (status 200), {len(response.text)} bytes:")
        print(response.text)
    elif response.status_code == 404:
        print("Status 404 — no robots file found. "
              "(A missing file is not permission, it is just a missing file.)")
    else:
        print(f"Unexpected status {response.status_code}")


if __name__ == "__main__":
    main()

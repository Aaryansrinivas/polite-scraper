# The polite scraper — FlyRank Internship, Backend Track, W5 · A9

A small, polite scraping pipeline for [Books to Scrape](https://books.toscrape.com):
downloads the first 3 catalogue pages, visits all 60 book pages, turns messy HTML
into clean, checked JSON — without crashing on a broken page, and with an honest
report at the end of every run.

## Target classification (Stage 0)

- **Site:** `books.toscrape.com` — a public sandbox built for scraping practice.
  Its own homepage states "We love being scraped!" — that sentence is the
  permission this assignment relies on, and it's the only kind of site this
  project touches.
- **Scope:** the first **3 catalogue pages only** (`page-1.html` → `page-3.html`,
  followed via the site's own "next" link), and the ~60 book detail pages linked
  from them. No other pages, no other domains.
- **robots.txt result:** requesting `https://books.toscrape.com/robots.txt`
  returns **HTTP 404 — no robots file found**. A missing file is not permission
  on its own, but combined with the site's stated purpose as a scraping sandbox,
  fetching a handful of public pages at a slow, identified, capped rate is
  appropriate here.
- **Data collected:** title, price, availability, star rating, and description
  text that is already present in the server-rendered HTML — nothing behind a
  login, paywall, or form submission.

> I will not reuse this code on another site without checking its rules and
> terms first.

## Quick start

```bash
git clone <this-repo-url>
cd scraper
pip install -r requirements.txt

# Stage 0 (optional, already recorded above) — re-check the target yourself:
python -m src.check_target

# Full run:
python -m src.main

# Stage 5 checkpoint — prove one broken page doesn't kill the run:
python -m src.main --inject-broken-url

# Unit tests (no network needed, run against saved fixtures):
python -m pytest tests/ -v
```

Requires **Python 3.10+**. No database, no paid API, no proxy, no credit card.

Output lands in `output/books.json`, `output/errors.json`, and
`output/run-report.json`. Cached HTML lives in `cache/` (gitignored).

## Record schema

```json
{
  "title": "A Light in the Attic",
  "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "price_text": "£51.77",
  "price_gbp": 51.77,
  "availability_text": "In stock (22 available)",
  "rating_text": "Three",
  "rating_num": 3,
  "description": "It's hard to imagine a world without A Light in the Attic...",
  "source_page": "https://books.toscrape.com/catalogue/page-1.html",
  "fetched_at": "2026-08-17T10:00:00Z"
}
```

- `product_url` is each record's **canonical URL** and identity — a rerun
  updates records, it never duplicates them (idempotent).
- `price_gbp` is a real number derived from `price_text`; both are kept side
  by side.
- `description` is `null`, never invented, when the page has none.
- `source_page` + `fetched_at` are the record's **provenance** — where and
  when the fact was collected.
- Records that fail schema validation go to `errors.json` with a reason —
  never into `books.json`.

## Politeness rules this scraper follows

- **User-agent:** `FlyRankInternshipA9/1.0 (+https://github.com/YOUR_USERNAME/YOUR_REPO)`
  on every request — a site owner can see who this is in their logs.
- **Timeout:** 10 seconds per request; never waits forever.
- **Delay:** at least 0.6s between real requests to the live site. Cached
  pages incur no delay — they never leave the machine.
- **Cache:** every fetched page is saved to `cache/`; a second run reads the
  saved copy first (`CACHE HIT` vs `FETCH` printed to the console).
- **Status check:** only HTTP 200 is treated as a page to parse. `404`/`403`
  are logged and skipped, never retried. `5xx` and timeouts get **one** retry
  with a short backoff.

## Sample run report

```json
{
  "start_time": "2026-08-17T10:00:00Z",
  "end_time": "2026-08-17T10:01:12Z",
  "duration_seconds": 72.4,
  "catalogue_pages_fetched": 3,
  "detail_pages_attempted": 60,
  "real_requests": 63,
  "cache_hits": 0,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0,
  "failed_urls": []
}
```
*(Replace this with your own `output/run-report.json` after a real run,
per the Stage 6 checkpoint.)*

## Why no browser was needed

The book title, price, availability, rating, and description are all present
directly in the HTML the server sends for each page — there is no
JavaScript-rendered data layer to wait on. A browser (e.g. Playwright) would
only add startup cost and memory for content that a plain HTTP GET already
returns, so this assignment's core pipeline uses `requests` + `BeautifulSoup`
only.

## Ethics note

- Use an official API instead of scraping whenever one exists — Books to
  Scrape offers none, which is part of why it's built for this exercise.
- Never bypass logins, paywalls, CAPTCHAs, or an explicit block from a site.
- Collect only the fields actually needed for the task, at a rate a human
  visitor wouldn't consider excessive.
- If a site's `robots.txt` or terms say no, that's the end of it — a missing
  robots file is not itself a green light on a site that hadn't stated it was
  a practice sandbox.

## One honest limitation

Retry logic here is a single retry with a fixed backoff (no exponential
backoff, no `Retry-After` header handling, no structured logs) — that's
explicitly saved for next week's assignment (A16). Description text longer
than what's shown in the truncated catalogue view is fetched from the detail
page but not otherwise cleaned (e.g. embedded HTML entities beyond what
BeautifulSoup decodes automatically are left as-is).

## Project layout

```
scraper/
├── README.md
├── requirements.txt
├── .gitignore
├── src/
│   ├── check_target.py   # Stage 0 — robots.txt check
│   ├── fetcher.py         # Stage 1 & 5 — polite fetch, cache, retry
│   ├── extractor.py       # Stage 2 & 3 — HTML -> raw fields
│   ├── schema.py           # Stage 4 — RawRecord / BookRecord (pydantic)
│   └── main.py              # Orchestrates the full run + report
├── tests/
│   └── test_parser.py     # 7 unit tests against saved fixtures
├── cache/                    # gitignored — saved HTML
└── output/                   # gitignored — books.json, errors.json, run-report.json
```

## Suggested commit sequence (7+ commits)

1. `Stage 0: classify scraping target`
2. `Stage 1: fetch and cache HTML`
3. `Stage 2: discover three catalogue pages`
4. `Stage 3: extract book details`
5. `Stage 4: validate normalized records`
6. `Stage 5: survive failures, report the run`
7. `Stage 6: publish scraper evidence`

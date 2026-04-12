# RSS Fetcher Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the RSS fetcher module that ingests categorized RSS feeds, filters by time window, dedupes by URL, and returns structured article data.

**Architecture:** Sequential fetcher using feedparser. Config holds categorized feed URLs. Each feed is fetched, parsed, filtered by 24-hour window, then all results are deduped by URL. Returns tuple of (articles list, summary dict).

**Tech Stack:** Python 3.11+, feedparser, python-dateutil

---

## File Structure

| File | Responsibility |
|------|----------------|
| `config.py` | Settings (LOOKBACK_HOURS, FEEDS dict, PERSONA) |
| `ingest/__init__.py` | Package marker, exports `fetch_feeds` |
| `ingest/rss_fetcher.py` | All fetching logic and helper functions |
| `main.py` | Orchestrator skeleton (calls fetch_feeds, prints results) |
| `requirements.txt` | Python dependencies |
| `tests/test_rss_fetcher.py` | Unit tests for rss_fetcher |
| `docs/testing.md` | Manual testing guide |
| `.gitignore` | Standard Python ignores |

---

## Chunk 1: Project Setup

### Task 1: Create requirements.txt

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```
feedparser>=6.0.0
python-dateutil>=2.8.0
pytest>=7.0.0
```

- [ ] **Step 2: Commit**

```bash
git add requirements.txt
git commit -m "Add requirements.txt with feedparser, dateutil, pytest"
```

---

### Task 2: Create .gitignore

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: Create .gitignore**

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
*.egg-info/
dist/
build/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Environment
.env
.env.local

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "Add .gitignore for Python project"
```

---

### Task 3: Create config.py

**Files:**
- Create: `config.py`

- [ ] **Step 1: Create config.py**

```python
"""
Watcher configuration.

Edit FEEDS to add your RSS feed URLs, organized by category.
Adjust LOOKBACK_HOURS for testing (default: 24 hours).
"""

# Time settings
LOOKBACK_HOURS = 24  # How far back to fetch articles

# RSS feeds organized by category
# Add your feeds here - the category names will appear in the digest
FEEDS = {
    "AI Tools": [
        # Example: "https://openai.com/blog/rss.xml",
    ],
    "Tech News": [
        # Example: "https://techcrunch.com/feed/",
    ],
}

# Persona for Claude prompts (used in Stage 2)
PERSONA = """
You are summarizing news for a [role] who cares about [topics].
Focus on [priorities].
"""
```

- [ ] **Step 2: Commit**

```bash
git add config.py
git commit -m "Add config.py with FEEDS, LOOKBACK_HOURS, PERSONA"
```

---

### Task 4: Create package structure

**Files:**
- Create: `ingest/__init__.py`
- Create: `synthesize/__init__.py`
- Create: `deliver/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create directories and __init__.py files**

```bash
mkdir -p ingest synthesize deliver tests
```

- [ ] **Step 2: Create ingest/__init__.py**

```python
"""Ingest module - fetches content from various sources."""

from ingest.rss_fetcher import fetch_feeds

__all__ = ["fetch_feeds"]
```

- [ ] **Step 3: Create placeholder __init__.py files**

synthesize/__init__.py:
```python
"""Synthesize module - processes content with Claude API."""
```

deliver/__init__.py:
```python
"""Deliver module - sends digest via email and Slack."""
```

tests/__init__.py:
```python
"""Test suite for Watcher."""
```

- [ ] **Step 4: Commit**

```bash
git add ingest/ synthesize/ deliver/ tests/
git commit -m "Add package structure for ingest, synthesize, deliver, tests"
```

---

## Chunk 2: RSS Fetcher Core (TDD)

### Task 5: Test and implement _extract_source

**Files:**
- Create: `tests/test_rss_fetcher.py`
- Create: `ingest/rss_fetcher.py`

- [ ] **Step 1: Write failing test for _extract_source**

tests/test_rss_fetcher.py:
```python
"""Tests for RSS fetcher module."""

from ingest.rss_fetcher import _extract_source


class TestExtractSource:
    def test_extracts_domain_from_url(self):
        assert _extract_source("https://techcrunch.com/feed/") == "techcrunch.com"

    def test_handles_www_prefix(self):
        assert _extract_source("https://www.example.com/rss") == "www.example.com"

    def test_handles_subdomain(self):
        assert _extract_source("https://blog.openai.com/feed") == "blog.openai.com"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_rss_fetcher.py -v
```

Expected: FAIL with "ModuleNotFoundError" or "ImportError"

- [ ] **Step 3: Write minimal implementation**

ingest/rss_fetcher.py:
```python
"""
RSS feed fetcher for Watcher.

Fetches articles from configured RSS feeds, filters by time window,
dedupes by URL, and returns structured data for synthesis.
"""

import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _extract_source(feed_url: str) -> str:
    """Extract domain from feed URL for source attribution."""
    return urlparse(feed_url).netloc
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_rss_fetcher.py::TestExtractSource -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add tests/test_rss_fetcher.py ingest/rss_fetcher.py
git commit -m "feat: add _extract_source function with tests"
```

---

### Task 6: Test and implement _get_cutoff_time

**Files:**
- Modify: `tests/test_rss_fetcher.py`
- Modify: `ingest/rss_fetcher.py`

- [ ] **Step 1: Write failing test for _get_cutoff_time**

Add to tests/test_rss_fetcher.py:
```python
from datetime import datetime, timezone
from unittest.mock import patch

from ingest.rss_fetcher import _extract_source, _get_cutoff_time


class TestGetCutoffTime:
    @patch("ingest.rss_fetcher.config")
    def test_returns_utc_datetime(self, mock_config):
        mock_config.LOOKBACK_HOURS = 24
        cutoff = _get_cutoff_time()
        assert cutoff.tzinfo == timezone.utc

    @patch("ingest.rss_fetcher.config")
    def test_respects_lookback_hours(self, mock_config):
        mock_config.LOOKBACK_HOURS = 48
        with patch("ingest.rss_fetcher.datetime") as mock_dt:
            fake_now = datetime(2026, 3, 29, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = fake_now
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            cutoff = _get_cutoff_time()
            # 48 hours before noon on March 29 = noon on March 27
            assert cutoff.day == 27
            assert cutoff.hour == 12
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_rss_fetcher.py::TestGetCutoffTime -v
```

Expected: FAIL with "ImportError" (function doesn't exist yet)

- [ ] **Step 3: Write minimal implementation**

Add to ingest/rss_fetcher.py (after imports):
```python
from datetime import datetime, timedelta, timezone

import config
```

Add function:
```python
def _get_cutoff_time() -> datetime:
    """Return UTC datetime for LOOKBACK_HOURS ago."""
    now = datetime.now(timezone.utc)
    return now - timedelta(hours=config.LOOKBACK_HOURS)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_rss_fetcher.py::TestGetCutoffTime -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add tests/test_rss_fetcher.py ingest/rss_fetcher.py
git commit -m "feat: add _get_cutoff_time function with tests"
```

---

### Task 7: Test and implement _parse_entry_date

**Files:**
- Modify: `tests/test_rss_fetcher.py`
- Modify: `ingest/rss_fetcher.py`

- [ ] **Step 1: Write failing test for _parse_entry_date**

Add to tests/test_rss_fetcher.py:
```python
import time

from ingest.rss_fetcher import _extract_source, _get_cutoff_time, _parse_entry_date


class TestParseEntryDate:
    def test_parses_published_parsed(self):
        entry = {"published_parsed": time.struct_time((2026, 3, 28, 14, 30, 0, 0, 0, 0))}
        result = _parse_entry_date(entry)
        assert result is not None
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 28
        assert result.tzinfo == timezone.utc

    def test_falls_back_to_updated_parsed(self):
        entry = {"updated_parsed": time.struct_time((2026, 3, 27, 10, 0, 0, 0, 0, 0))}
        result = _parse_entry_date(entry)
        assert result is not None
        assert result.day == 27

    def test_returns_none_if_no_date(self):
        entry = {"title": "No date here"}
        result = _parse_entry_date(entry)
        assert result is None

    def test_returns_none_for_invalid_date(self):
        entry = {"published_parsed": None}
        result = _parse_entry_date(entry)
        assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_rss_fetcher.py::TestParseEntryDate -v
```

Expected: FAIL with "ImportError"

- [ ] **Step 3: Write minimal implementation**

Add to ingest/rss_fetcher.py:
```python
from calendar import timegm


def _parse_entry_date(entry: dict) -> datetime | None:
    """
    Extract publication date from RSS entry.

    Checks published_parsed first, then updated_parsed.
    Returns None if no valid date found.
    """
    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field)
        if parsed:
            try:
                timestamp = timegm(parsed)
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            except (TypeError, ValueError, OverflowError):
                continue
    return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_rss_fetcher.py::TestParseEntryDate -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add tests/test_rss_fetcher.py ingest/rss_fetcher.py
git commit -m "feat: add _parse_entry_date function with tests"
```

---

### Task 8: Test and implement _is_within_window

**Files:**
- Modify: `tests/test_rss_fetcher.py`
- Modify: `ingest/rss_fetcher.py`

- [ ] **Step 1: Write failing test for _is_within_window**

Add to tests/test_rss_fetcher.py:
```python
from ingest.rss_fetcher import (
    _extract_source,
    _get_cutoff_time,
    _parse_entry_date,
    _is_within_window,
)


class TestIsWithinWindow:
    def test_returns_true_for_recent_entry(self):
        cutoff = datetime(2026, 3, 28, 0, 0, 0, tzinfo=timezone.utc)
        entry = {"published_parsed": time.struct_time((2026, 3, 28, 12, 0, 0, 0, 0, 0))}
        assert _is_within_window(entry, cutoff) is True

    def test_returns_false_for_old_entry(self):
        cutoff = datetime(2026, 3, 28, 0, 0, 0, tzinfo=timezone.utc)
        entry = {"published_parsed": time.struct_time((2026, 3, 27, 12, 0, 0, 0, 0, 0))}
        assert _is_within_window(entry, cutoff) is False

    def test_returns_false_for_entry_without_date(self):
        cutoff = datetime(2026, 3, 28, 0, 0, 0, tzinfo=timezone.utc)
        entry = {"title": "No date"}
        assert _is_within_window(entry, cutoff) is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_rss_fetcher.py::TestIsWithinWindow -v
```

Expected: FAIL with "ImportError"

- [ ] **Step 3: Write minimal implementation**

Add to ingest/rss_fetcher.py:
```python
def _is_within_window(entry: dict, cutoff_time: datetime) -> bool:
    """Check if entry was published after cutoff time."""
    entry_date = _parse_entry_date(entry)
    if entry_date is None:
        return False
    return entry_date >= cutoff_time
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_rss_fetcher.py::TestIsWithinWindow -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add tests/test_rss_fetcher.py ingest/rss_fetcher.py
git commit -m "feat: add _is_within_window function with tests"
```

---

### Task 9: Test and implement _dedupe_by_url

**Files:**
- Modify: `tests/test_rss_fetcher.py`
- Modify: `ingest/rss_fetcher.py`

- [ ] **Step 1: Write failing test for _dedupe_by_url**

Add to tests/test_rss_fetcher.py:
```python
from ingest.rss_fetcher import (
    _extract_source,
    _get_cutoff_time,
    _parse_entry_date,
    _is_within_window,
    _dedupe_by_url,
)


class TestDedupeByUrl:
    def test_removes_duplicate_urls(self):
        articles = [
            {"link": "https://example.com/1", "title": "First"},
            {"link": "https://example.com/2", "title": "Second"},
            {"link": "https://example.com/1", "title": "First (dupe)"},
        ]
        result = _dedupe_by_url(articles)
        assert len(result) == 2
        links = [a["link"] for a in result]
        assert "https://example.com/1" in links
        assert "https://example.com/2" in links

    def test_keeps_first_occurrence(self):
        articles = [
            {"link": "https://example.com/1", "title": "First"},
            {"link": "https://example.com/1", "title": "Duplicate"},
        ]
        result = _dedupe_by_url(articles)
        assert len(result) == 1
        assert result[0]["title"] == "First"

    def test_handles_empty_list(self):
        assert _dedupe_by_url([]) == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_rss_fetcher.py::TestDedupeByUrl -v
```

Expected: FAIL with "ImportError"

- [ ] **Step 3: Write minimal implementation**

Add to ingest/rss_fetcher.py:
```python
def _dedupe_by_url(articles: list[dict]) -> list[dict]:
    """Remove duplicate articles by URL, keeping first occurrence."""
    seen_urls = set()
    unique_articles = []
    for article in articles:
        url = article.get("link")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)
    return unique_articles
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_rss_fetcher.py::TestDedupeByUrl -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add tests/test_rss_fetcher.py ingest/rss_fetcher.py
git commit -m "feat: add _dedupe_by_url function with tests"
```

---

## Chunk 3: Feed Fetching

### Task 10: Test and implement _fetch_single_feed

**Files:**
- Modify: `tests/test_rss_fetcher.py`
- Modify: `ingest/rss_fetcher.py`

- [ ] **Step 1: Write failing test for _fetch_single_feed**

Add to tests/test_rss_fetcher.py:
```python
from unittest.mock import MagicMock

from ingest.rss_fetcher import (
    _extract_source,
    _get_cutoff_time,
    _parse_entry_date,
    _is_within_window,
    _dedupe_by_url,
    _fetch_single_feed,
)


class TestFetchSingleFeed:
    @patch("ingest.rss_fetcher.feedparser")
    @patch("ingest.rss_fetcher._get_cutoff_time")
    def test_returns_articles_within_window(self, mock_cutoff, mock_feedparser):
        mock_cutoff.return_value = datetime(2026, 3, 28, 0, 0, 0, tzinfo=timezone.utc)
        mock_feedparser.parse.return_value = MagicMock(
            bozo=False,
            entries=[
                {
                    "title": "Recent Article",
                    "summary": "Summary here",
                    "link": "https://example.com/recent",
                    "published_parsed": time.struct_time((2026, 3, 28, 12, 0, 0, 0, 0, 0)),
                },
                {
                    "title": "Old Article",
                    "summary": "Old summary",
                    "link": "https://example.com/old",
                    "published_parsed": time.struct_time((2026, 3, 20, 12, 0, 0, 0, 0, 0)),
                },
            ],
        )
        articles, error = _fetch_single_feed("https://example.com/feed", "Tech")
        assert len(articles) == 1
        assert articles[0]["title"] == "Recent Article"
        assert articles[0]["category"] == "Tech"
        assert articles[0]["source"] == "example.com"
        assert error is None

    @patch("ingest.rss_fetcher.feedparser")
    def test_returns_error_for_failed_feed(self, mock_feedparser):
        mock_feedparser.parse.return_value = MagicMock(
            bozo=True,
            bozo_exception=Exception("Network error"),
            entries=[],
        )
        articles, error = _fetch_single_feed("https://broken.com/feed", "Tech")
        assert articles == []
        assert error is not None
        assert "broken.com" in error
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_rss_fetcher.py::TestFetchSingleFeed -v
```

Expected: FAIL with "ImportError"

- [ ] **Step 3: Write implementation**

Add to top of ingest/rss_fetcher.py (imports):
```python
import feedparser
```

Add function:
```python
def _fetch_single_feed(feed_url: str, category: str) -> tuple[list[dict], str | None]:
    """
    Fetch a single RSS feed and return articles within time window.

    Returns:
        Tuple of (articles list, error message or None)
    """
    try:
        feed = feedparser.parse(feed_url)

        if feed.bozo and not feed.entries:
            error_msg = f"Failed to fetch {feed_url}: {feed.bozo_exception}"
            logger.warning(error_msg)
            return [], error_msg

        cutoff = _get_cutoff_time()
        source = _extract_source(feed_url)
        articles = []

        for entry in feed.entries:
            if not _is_within_window(entry, cutoff):
                continue

            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()

            if not title or not link:
                logger.debug(f"Skipping entry without title or link in {feed_url}")
                continue

            entry_date = _parse_entry_date(entry)

            articles.append({
                "title": title,
                "summary": entry.get("summary", "").strip(),
                "link": link,
                "source": source,
                "category": category,
                "published": entry_date.isoformat() if entry_date else None,
            })

        return articles, None

    except Exception as e:
        error_msg = f"Failed to fetch {feed_url}: {e}"
        logger.warning(error_msg)
        return [], error_msg
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_rss_fetcher.py::TestFetchSingleFeed -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add tests/test_rss_fetcher.py ingest/rss_fetcher.py
git commit -m "feat: add _fetch_single_feed function with tests"
```

---

### Task 11: Test and implement fetch_feeds (main entry point)

**Files:**
- Modify: `tests/test_rss_fetcher.py`
- Modify: `ingest/rss_fetcher.py`

- [ ] **Step 1: Write failing test for fetch_feeds**

Add to tests/test_rss_fetcher.py:
```python
from ingest.rss_fetcher import fetch_feeds


class TestFetchFeeds:
    @patch("ingest.rss_fetcher.config")
    @patch("ingest.rss_fetcher._fetch_single_feed")
    def test_fetches_all_feeds_from_config(self, mock_fetch, mock_config):
        mock_config.FEEDS = {
            "AI": ["https://ai.com/feed"],
            "Tech": ["https://tech.com/feed"],
        }
        mock_fetch.side_effect = [
            ([{"title": "AI Article", "link": "https://ai.com/1"}], None),
            ([{"title": "Tech Article", "link": "https://tech.com/1"}], None),
        ]

        articles, summary = fetch_feeds()

        assert len(articles) == 2
        assert summary["total_feeds"] == 2
        assert summary["successful"] == 2
        assert summary["failed"] == 0
        assert summary["articles_found"] == 2

    @patch("ingest.rss_fetcher.config")
    @patch("ingest.rss_fetcher._fetch_single_feed")
    def test_handles_failed_feeds(self, mock_fetch, mock_config):
        mock_config.FEEDS = {
            "AI": ["https://ai.com/feed", "https://broken.com/feed"],
        }
        mock_fetch.side_effect = [
            ([{"title": "AI Article", "link": "https://ai.com/1"}], None),
            ([], "Network error"),
        ]

        articles, summary = fetch_feeds()

        assert len(articles) == 1
        assert summary["total_feeds"] == 2
        assert summary["successful"] == 1
        assert summary["failed"] == 1
        assert "https://broken.com/feed" in summary["failed_feeds"]

    @patch("ingest.rss_fetcher.config")
    def test_handles_empty_config(self, mock_config):
        mock_config.FEEDS = {}

        articles, summary = fetch_feeds()

        assert articles == []
        assert summary["total_feeds"] == 0

    @patch("ingest.rss_fetcher.config")
    @patch("ingest.rss_fetcher._fetch_single_feed")
    def test_dedupes_across_feeds(self, mock_fetch, mock_config):
        mock_config.FEEDS = {
            "AI": ["https://ai.com/feed"],
            "Tech": ["https://tech.com/feed"],
        }
        # Same article URL appears in both feeds
        mock_fetch.side_effect = [
            ([{"title": "Shared Article", "link": "https://shared.com/1"}], None),
            ([{"title": "Shared Article Copy", "link": "https://shared.com/1"}], None),
        ]

        articles, summary = fetch_feeds()

        assert len(articles) == 1  # Deduped
        assert summary["articles_found"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_rss_fetcher.py::TestFetchFeeds -v
```

Expected: FAIL with "ImportError"

- [ ] **Step 3: Write implementation**

Add to ingest/rss_fetcher.py:
```python
def fetch_feeds() -> tuple[list[dict], dict]:
    """
    Fetch all RSS feeds from config and return articles.

    Returns:
        Tuple of:
        - List of article dicts (deduped by URL)
        - Summary dict with fetch statistics
    """
    feeds_config = getattr(config, "FEEDS", {})

    if not feeds_config:
        logger.warning("No feeds configured in config.FEEDS")
        return [], {
            "total_feeds": 0,
            "successful": 0,
            "failed": 0,
            "failed_feeds": [],
            "articles_found": 0,
        }

    all_articles = []
    failed_feeds = []
    total_feeds = 0

    for category, urls in feeds_config.items():
        if not urls:
            logger.debug(f"Skipping empty category: {category}")
            continue

        for url in urls:
            total_feeds += 1
            articles, error = _fetch_single_feed(url, category)

            if error:
                failed_feeds.append(url)
            else:
                all_articles.extend(articles)

    # Dedupe by URL
    unique_articles = _dedupe_by_url(all_articles)

    summary = {
        "total_feeds": total_feeds,
        "successful": total_feeds - len(failed_feeds),
        "failed": len(failed_feeds),
        "failed_feeds": failed_feeds,
        "articles_found": len(unique_articles),
    }

    logger.info(
        f"Fetched {summary['articles_found']} articles from "
        f"{summary['successful']}/{summary['total_feeds']} feeds"
    )

    if failed_feeds:
        logger.warning(f"Failed feeds: {failed_feeds}")

    return unique_articles, summary
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_rss_fetcher.py::TestFetchFeeds -v
```

Expected: 4 passed

- [ ] **Step 5: Run all tests**

```bash
python -m pytest tests/test_rss_fetcher.py -v
```

Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add tests/test_rss_fetcher.py ingest/rss_fetcher.py
git commit -m "feat: add fetch_feeds main entry point with tests"
```

---

## Chunk 4: Main Orchestrator and Docs

### Task 12: Create main.py

**Files:**
- Create: `main.py`

- [ ] **Step 1: Create main.py**

```python
"""
Watcher - Personal AI News Digest

Orchestrates the three stages:
1. Ingest - Fetch content from RSS, Gmail, Substack
2. Synthesize - Process with Claude API
3. Deliver - Send via email and Slack

Usage:
    python main.py
"""

import logging
import json

from ingest import fetch_feeds

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Run the Watcher digest pipeline."""
    logger.info("Starting Watcher digest...")

    # Stage 1: Ingest
    logger.info("Stage 1: Fetching RSS feeds...")
    articles, summary = fetch_feeds()

    logger.info(f"Ingest complete: {summary}")

    # Print results for now (Stage 2 & 3 will process these)
    print("\n" + "=" * 60)
    print("WATCHER DIGEST - RSS ARTICLES")
    print("=" * 60)
    print(f"\nFetched {summary['articles_found']} articles from {summary['successful']}/{summary['total_feeds']} feeds")

    if summary["failed"] > 0:
        print(f"\nWarning: {summary['failed']} feeds failed:")
        for url in summary["failed_feeds"]:
            print(f"  - {url}")

    print("\n" + "-" * 60)

    # Group by category
    by_category = {}
    for article in articles:
        cat = article.get("category", "Uncategorized")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(article)

    for category, cat_articles in by_category.items():
        print(f"\n## {category} ({len(cat_articles)} articles)\n")
        for article in cat_articles:
            print(f"- {article['title']}")
            print(f"  Source: {article['source']} | {article['published']}")
            print(f"  Link: {article['link']}")
            if article.get("summary"):
                # Truncate long summaries
                summary_text = article["summary"][:200]
                if len(article["summary"]) > 200:
                    summary_text += "..."
                print(f"  {summary_text}")
            print()

    # Stage 2: Synthesize (TODO)
    logger.info("Stage 2: Synthesize - Not yet implemented")

    # Stage 3: Deliver (TODO)
    logger.info("Stage 3: Deliver - Not yet implemented")

    logger.info("Watcher digest complete.")

    return articles, summary


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test that main.py runs**

```bash
python main.py
```

Expected: Runs without error, shows "0 articles from 0/0 feeds" (no feeds configured yet)

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "Add main.py orchestrator skeleton"
```

---

### Task 13: Create docs/testing.md

**Files:**
- Create: `docs/testing.md`

- [ ] **Step 1: Create docs/testing.md**

```markdown
# Watcher Testing Guide

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run unit tests
python -m pytest tests/ -v

# Run the fetcher manually
python main.py
```

## Testing RSS Fetcher

### 1. Add Test Feeds

Edit `config.py` and add some real RSS feeds:

```python
FEEDS = {
    "AI Tools": [
        "https://openai.com/blog/rss.xml",
        "https://blog.anthropic.com/rss.xml",
    ],
    "Tech News": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
    ],
}
```

### 2. Adjust Time Window (Optional)

If feeds haven't published recently, increase the lookback:

```python
LOOKBACK_HOURS = 72  # 3 days instead of 24 hours
```

### 3. Run and Verify

```bash
python main.py
```

Check that:
- Articles are grouped by category
- Each article has title, source, link, published date
- No duplicate URLs appear
- Failed feeds are logged (if any)

## Unit Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test class
python -m pytest tests/test_rss_fetcher.py::TestFetchFeeds -v

# Run with coverage
python -m pytest tests/ --cov=ingest --cov-report=term-missing
```

## Decisions to Revisit

| Decision | Current | Revisit When |
|----------|---------|--------------|
| RSS metadata only | Using title/summary from feed | If Claude needs more context, add full article fetching |
| Simple sequential | Fetch feeds one by one | If feed count exceeds 50+, consider concurrent fetching |
| No retry logic | Single attempt per feed | If transient failures become frequent, add single retry |

## Troubleshooting

### "No feeds configured"
Add feeds to `config.py` in the `FEEDS` dict.

### "0 articles found" with feeds configured
- Check if feeds have published in the last 24 hours
- Increase `LOOKBACK_HOURS` to 48 or 72
- Verify feed URLs are correct (test in browser)

### Feed errors
Check the logs for specific error messages. Common issues:
- Network timeouts
- Invalid RSS/XML format
- Feed URL changed or deprecated
```

- [ ] **Step 2: Commit**

```bash
git add docs/testing.md
git commit -m "Add docs/testing.md with testing guide"
```

---

### Task 14: Final verification and cleanup

- [ ] **Step 1: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: All tests pass

- [ ] **Step 2: Run main.py**

```bash
python main.py
```

Expected: Runs without error

- [ ] **Step 3: Verify project structure**

```bash
ls -la
ls -la ingest/
ls -la tests/
ls -la docs/
```

Expected structure:
```
.
├── .gitignore
├── config.py
├── main.py
├── requirements.txt
├── docs/
│   ├── spec.md
│   ├── plan.md
│   └── testing.md
├── ingest/
│   ├── __init__.py
│   └── rss_fetcher.py
├── synthesize/
│   └── __init__.py
├── deliver/
│   └── __init__.py
└── tests/
    ├── __init__.py
    └── test_rss_fetcher.py
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git status
```

If any uncommitted changes, commit them:

```bash
git commit -m "Complete Stage 1: RSS Fetcher implementation"
```

---

## Summary

Stage 1 is complete when:

1. All unit tests pass (`python -m pytest tests/ -v`)
2. `python main.py` runs without error
3. Adding real feeds to `config.py` fetches and displays articles
4. Articles are deduped, filtered by time, and grouped by category

---

# Distributing Watcher to Others

We have two paths to make Watcher available to users: one for technical users who want to integrate it into their AI workflows, and one for non-technical users who just want daily digests in Slack.

---

## Plan A: MCP Server (For Technical Users)

### What It Is

MCP (Model Context Protocol) lets AI assistants like Claude connect to external tools. We build an MCP server that wraps Watcher, so users can add it to their Claude Desktop or Claude Code setup and ask their AI to fetch news digests on demand.

### How Users Would Use It

1. Install our package: `pip install watcher-mcp`
2. Add a few lines to their Claude config file
3. Provide their own Anthropic API key
4. Ask Claude: "Get me today's AI news digest"

### What We Build

A thin wrapper around our existing code that exposes four capabilities:
- **Fetch news** - Get articles from the last N hours, optionally filtered by category
- **Generate digest** - Create a synthesized summary of recent news
- **List categories** - Show what feed categories are available
- **List personas** - Show what synthesis styles are available

### Why This Approach

- Users bring their own API key, so we have zero operating costs
- Works with Claude Desktop, Claude Code, Cursor, and other MCP-compatible tools
- Can ship in 2-3 days
- Good way to build community and get early feedback

### Limitations

- Only works in the Claude/MCP ecosystem (won't work with OpenAI, LangChain, etc.)
- Harder to monetize since it's an installable package
- Users need to be somewhat technical to set it up

---

## Plan B: Hosted Slack Service (For Non-Technical Users)

### What It Is

A web service where users sign up, connect their Slack, pick their preferences, and automatically get daily digests delivered. No technical setup required.

### How Users Would Use It

1. Visit our website and sign up with email
2. Paste in their Slack webhook URL (we provide simple instructions)
3. Check the boxes for which news categories they care about
4. Pick a persona that matches how they want news framed
5. Choose what time they want their daily digest
6. Done - they get a digest in Slack every day at their chosen time

### What We Build

Three pieces:
1. **Simple website** - Landing page explaining Watcher, login, and a configuration form
2. **Database** - Stores user preferences (which categories, which persona, what time)
3. **Scheduler** - Runs hourly, checks who needs a digest now, generates and delivers it

We use Supabase for the database and auth (free tier is generous), and GitHub Actions to run the scheduler (also free).

### Why This Approach

- Reaches non-technical users who would never install a package
- Natural subscription business: we can charge $9-15/month
- We control the entire experience
- Can expand later to web dashboard, mobile app, etc.

### Limitations

- We pay for Claude API usage (roughly $1.50 per user per month)
- More to build and maintain
- Takes about a week to get the MVP working

---

## Monetization Comparison

### MCP Server (Plan A)
- Hard to charge for an open source package
- Could offer premium feed bundles for a one-time fee
- Best approach: give it away free to build adoption

### Hosted Service (Plan B)
- Natural subscription model: free tier (limited) + paid tier ($9/mo)
- At $9/month with $1.50 in costs, that's healthy margin
- Can add team plans later ($29/mo)

---

## What to Build First

**If we want speed and feedback:** Build the MCP server first. It's faster (2-3 days), costs nothing to run, and lets us validate the product with power users.

**If we want revenue sooner:** Build the hosted service first. It takes longer (1 week) but has a clearer path to charging money.

**If we're ambitious:** Build both. The core Watcher code stays the same - we're just adding two different wrappers. Technical users get MCP, everyone else gets the hosted service.

---

## Next Steps

1. Decide which to build first (or both)
2. For MCP: Create the server wrapper, publish to PyPI, write setup docs
3. For Hosted: Set up Supabase, build the scheduler, create the simple web UI

---

# Chat About Info

Enable two-way Slack communication where users can ask questions about stored articles at any time.

## Capabilities

| Feature | Example | How It Works |
|---------|---------|--------------|
| **Basic Q&A** | "what's the deal with OpenClaw?" | Search articles → Claude answers |
| **Historical queries** | "all Claude updates this month" | Search across 30 days of articles |
| **Reasoning/comparison** | "compare Cursor vs Claude Code" | Find relevant articles → Claude analyzes |
| **Deep dive** | "deep dive on the Linear article" | Fetch full article → detailed summary |
| **Today's digest** | "summarize today's themes" | Return stored digest |

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   main.py       │     │  chat_server.py │
│  (digest mode)  │     │  (chat mode)    │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │  saves                │  reads
         ▼                       ▼
    ┌─────────────────────────────────┐
    │     data/articles.json          │
    │  (accumulated articles + digest)│
    └─────────────────────────────────┘
                    │
                    │  context
                    ▼
              ┌───────────┐
              │  Claude   │
              │   API     │
              └───────────┘
```

---

## New File Structure

```
watcher/
├── main.py                    # Modify: save articles after fetching
├── chat_server.py             # NEW: entry point for chat bot
├── config.py                  # Modify: add storage/chat settings
│
├── storage/                   # NEW MODULE
│   ├── __init__.py
│   └── article_store.py       # JSON storage with accumulation
│
├── chat/                      # NEW MODULE
│   ├── __init__.py
│   ├── slack_bot.py           # Socket Mode event handlers
│   └── qa_handler.py          # Q&A + deep dive logic
│
├── data/                      # NEW (created at runtime)
│   └── articles.json          # Accumulated articles + latest digest
│
└── tests/
    ├── test_article_store.py  # NEW
    └── test_qa_handler.py     # NEW
```

---

## Implementation Steps

### Step 1: Create Storage Module (with Accumulation)

**Files:** `storage/__init__.py`, `storage/article_store.py`

- [ ] Create `storage/` directory
- [ ] Implement `ArticleStore` class:
  - `add_articles(articles, digest)` - append new articles (don't overwrite)
  - `get_articles(days=None)` - filter by age
  - `get_digest()` - latest digest
  - `search(query, days=None)` - keyword search
  - `cleanup_old()` - remove articles older than retention period
- [ ] Write tests for storage
- [ ] Commit

**Storage schema:**
```json
{
  "last_updated": "2025-01-15T10:00:00Z",
  "latest_digest": { /* most recent synthesis */ },
  "articles": [
    {
      "id": "abc123",
      "title": "Article Title",
      "content": "Truncated content (500 words)...",
      "link": "https://...",
      "source": "every.to",
      "category": "AI Tools",
      "published": "2025-01-15T08:00:00Z",
      "fetched": "2025-01-15T10:00:00Z"
    }
  ]
}
```

### Step 2: Modify main.py to Save Articles

**File:** `main.py`

- [ ] Import `ArticleStore`
- [ ] After synthesis, call `store.add_articles(articles, digest)`
- [ ] Call `store.cleanup_old()` to remove stale articles
- [ ] Commit

### Step 3: Create Q&A Handler (with Deep Dive)

**File:** `chat/qa_handler.py`

- [ ] Create `chat/` directory
- [ ] Implement `QAHandler` class:
  - `handle(message)` - routes to appropriate method
  - `answer_question(question)` - search + Claude
  - `deep_dive(article_identifier)` - fetch full article + Claude
  - `get_history(topic, days)` - historical search
  - `summarize_digest()` - today's digest
  - `_fetch_full_article(url)` - uses trafilatura
- [ ] Write tests with mocked Claude
- [ ] Commit

### Step 4: Create Slack Bot

**File:** `chat/slack_bot.py`

- [ ] Install `slack-bolt`: add to requirements.txt
- [ ] Implement Socket Mode handlers:
  - `@app.event("app_mention")` - handle @watcher mentions
  - `@app.event("message")` - handle DMs
- [ ] Add "Thinking..." indicator while processing
- [ ] Commit

### Step 5: Create Chat Server Entry Point

**File:** `chat_server.py`

- [ ] Create entry point that calls `start_bot()`
- [ ] Add logging configuration
- [ ] Commit

### Step 6: Update Config

**File:** `config.py`

- [ ] Add `STORAGE_PATH = "data/articles.json"`
- [ ] Add `RETENTION_DAYS = 30`
- [ ] Add `CHAT_MODEL`, `MAX_CONTEXT_ARTICLES`, `MAX_CONTEXT_CHARS`
- [ ] Commit

### Step 7: Update Environment

**Files:** `.env.example`, `requirements.txt`

- [ ] Add `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` to `.env.example`
- [ ] Add `slack-bolt>=1.18.0` to requirements.txt
- [ ] Commit

---

## Slack App Setup (Manual)

1. **Create app** at https://api.slack.com/apps
2. **Enable Socket Mode** → generate App-Level Token (`xapp-...`)
3. **Add Bot Token Scopes:**
   - `app_mentions:read` - receive @watcher mentions
   - `chat:write` - send messages
   - `channels:history` - read channel context
   - `im:history` - read DM context
4. **Subscribe to events:** `app_mention`, `message.im`
5. **Install to workspace** → get Bot Token (`xoxb-...`)

---

## Usage

```bash
# Run digest (fetches articles, saves to storage, posts to Slack)
python main.py

# Start chat server (runs continuously)
python chat_server.py
```

**In Slack:**
```
@watcher what's the deal with OpenClaw?
→ Answers using relevant stored articles

@watcher deep dive on the Linear article
→ Fetches full article, provides detailed analysis

@watcher all Claude updates from the past 2 weeks
→ Searches historical articles, summarizes timeline

@watcher compare Cursor vs Claude Code based on recent coverage
→ Finds articles about both, Claude reasons through comparison
```

---

## Verification

- [ ] Run `python main.py` twice → check `data/articles.json` accumulates
- [ ] Run `python chat_server.py` → verify "Starting Watcher bot" logged
- [ ] `@watcher hello` → greeting response
- [ ] `@watcher [question about article]` → answer with sources
- [ ] `@watcher deep dive on [title]` → detailed analysis
- [ ] `pytest tests/test_article_store.py tests/test_qa_handler.py` → all pass

---

## Future Enhancements (Not in Scope)

- Vector embeddings for better search relevance
- Conversation memory (multi-turn threads)
- Slash commands (`/watcher digest`)
- Scheduled automatic digests
- Cloud deployment (Railway/Fly.io)

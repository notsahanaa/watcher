"""
RSS feed fetcher for Watcher.

Fetches articles from configured RSS feeds, filters by time window,
dedupes by URL, and returns structured data for synthesis.
"""

import logging
from calendar import timegm
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse

import feedparser

import config

logger = logging.getLogger(__name__)


def _extract_source(feed_url: str) -> str:
    """Extract domain from feed URL for source attribution."""
    return urlparse(feed_url).netloc


def _get_cutoff_time() -> datetime:
    """Return UTC datetime for LOOKBACK_HOURS ago."""
    now = datetime.now(timezone.utc)
    return now - timedelta(hours=config.LOOKBACK_HOURS)


def _parse_entry_date(entry: dict) -> Optional[datetime]:
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


def _is_within_window(entry: dict, cutoff_time: datetime) -> bool:
    """Check if entry was published after cutoff time."""
    entry_date = _parse_entry_date(entry)
    if entry_date is None:
        return False
    return entry_date >= cutoff_time


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


def _fetch_single_feed(feed_url: str, category: str) -> tuple[list[dict], Optional[str]]:
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


def fetch_feeds():
    """Fetch articles from configured RSS feeds."""
    pass

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


def fetch_feeds():
    """Fetch articles from configured RSS feeds."""
    pass

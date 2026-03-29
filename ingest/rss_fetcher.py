"""
RSS feed fetcher for Watcher.

Fetches articles from configured RSS feeds, filters by time window,
dedupes by URL, and returns structured data for synthesis.
"""

import logging
from datetime import datetime, timedelta, timezone
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


def fetch_feeds():
    """Fetch articles from configured RSS feeds."""
    pass

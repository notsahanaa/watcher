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
import trafilatura

import config

# Content settings
MAX_CONTENT_WORDS = 500  # Truncate article content to this many words

logger = logging.getLogger(__name__)


def _extract_source(feed_url: str) -> str:
    """Extract domain from feed URL for source attribution."""
    return urlparse(feed_url).netloc


def _truncate_to_words(text: str, max_words: int) -> str:
    """Truncate text to a maximum number of words."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."


def _fetch_article_content(url: str) -> Optional[str]:
    """
    Fetch and extract article text from URL using trafilatura.

    Returns:
        Extracted article text (truncated to MAX_CONTENT_WORDS), or None if failed.
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            logger.debug(f"Failed to download article: {url}")
            return None

        content = trafilatura.extract(downloaded)
        if not content:
            logger.debug(f"Failed to extract content from: {url}")
            return None

        return _truncate_to_words(content, MAX_CONTENT_WORDS)

    except Exception as e:
        logger.debug(f"Error fetching article content from {url}: {e}")
        return None


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

            # Fetch full article content
            content = _fetch_article_content(link)
            rss_summary = entry.get("summary", "").strip()

            articles.append({
                "title": title,
                "content": content if content else rss_summary,  # Fallback to RSS summary
                "summary": rss_summary,  # Keep original RSS summary
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

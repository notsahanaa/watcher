"""Tests for RSS fetcher module."""

import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from ingest.rss_fetcher import (
    _extract_source,
    _get_cutoff_time,
    _parse_entry_date,
    _is_within_window,
    _dedupe_by_url,
    _truncate_to_words,
    _fetch_article_content,
    _fetch_single_feed,
    fetch_feeds,
)


class TestExtractSource:
    def test_extracts_domain_from_url(self):
        assert _extract_source("https://techcrunch.com/feed/") == "techcrunch.com"

    def test_handles_www_prefix(self):
        assert _extract_source("https://www.example.com/rss") == "www.example.com"

    def test_handles_subdomain(self):
        assert _extract_source("https://blog.openai.com/feed") == "blog.openai.com"


class TestTruncateToWords:
    def test_returns_text_unchanged_if_under_limit(self):
        text = "one two three"
        assert _truncate_to_words(text, 10) == "one two three"

    def test_truncates_text_over_limit(self):
        text = "one two three four five six"
        result = _truncate_to_words(text, 3)
        assert result == "one two three..."

    def test_handles_exact_limit(self):
        text = "one two three"
        assert _truncate_to_words(text, 3) == "one two three"

    def test_handles_empty_string(self):
        assert _truncate_to_words("", 10) == ""


class TestFetchArticleContent:
    @patch("ingest.rss_fetcher.trafilatura")
    def test_returns_extracted_content(self, mock_trafilatura):
        mock_trafilatura.fetch_url.return_value = "<html>content</html>"
        mock_trafilatura.extract.return_value = "Article text here"

        result = _fetch_article_content("https://example.com/article")

        assert result == "Article text here"
        mock_trafilatura.fetch_url.assert_called_once_with("https://example.com/article")

    @patch("ingest.rss_fetcher.trafilatura")
    def test_truncates_long_content(self, mock_trafilatura):
        mock_trafilatura.fetch_url.return_value = "<html>content</html>"
        # Create content with 600 words
        long_content = " ".join(["word"] * 600)
        mock_trafilatura.extract.return_value = long_content

        result = _fetch_article_content("https://example.com/article")

        # Should be truncated to 500 words + "..." appended
        assert result.endswith("...")
        # 500 words, last one has "..." appended
        words = result.split()
        assert len(words) == 500
        assert words[-1] == "word..."

    @patch("ingest.rss_fetcher.trafilatura")
    def test_returns_none_on_download_failure(self, mock_trafilatura):
        mock_trafilatura.fetch_url.return_value = None

        result = _fetch_article_content("https://example.com/article")

        assert result is None

    @patch("ingest.rss_fetcher.trafilatura")
    def test_returns_none_on_extract_failure(self, mock_trafilatura):
        mock_trafilatura.fetch_url.return_value = "<html>content</html>"
        mock_trafilatura.extract.return_value = None

        result = _fetch_article_content("https://example.com/article")

        assert result is None


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


class TestFetchSingleFeed:
    @patch("ingest.rss_fetcher._fetch_article_content")
    @patch("ingest.rss_fetcher.feedparser")
    @patch("ingest.rss_fetcher._get_cutoff_time")
    def test_returns_articles_within_window(self, mock_cutoff, mock_feedparser, mock_fetch_content):
        mock_cutoff.return_value = datetime(2026, 3, 28, 0, 0, 0, tzinfo=timezone.utc)
        mock_fetch_content.return_value = "Full article content here"
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
        assert articles[0]["content"] == "Full article content here"
        assert articles[0]["summary"] == "Summary here"
        assert error is None

    @patch("ingest.rss_fetcher._fetch_article_content")
    @patch("ingest.rss_fetcher.feedparser")
    @patch("ingest.rss_fetcher._get_cutoff_time")
    def test_falls_back_to_summary_when_content_fetch_fails(self, mock_cutoff, mock_feedparser, mock_fetch_content):
        mock_cutoff.return_value = datetime(2026, 3, 28, 0, 0, 0, tzinfo=timezone.utc)
        mock_fetch_content.return_value = None  # Content fetch fails
        mock_feedparser.parse.return_value = MagicMock(
            bozo=False,
            entries=[
                {
                    "title": "Article",
                    "summary": "RSS summary fallback",
                    "link": "https://example.com/article",
                    "published_parsed": time.struct_time((2026, 3, 28, 12, 0, 0, 0, 0, 0)),
                },
            ],
        )
        articles, error = _fetch_single_feed("https://example.com/feed", "Tech")
        assert len(articles) == 1
        assert articles[0]["content"] == "RSS summary fallback"  # Falls back to summary

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

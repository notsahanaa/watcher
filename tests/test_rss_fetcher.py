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
    _fetch_single_feed,
)


class TestExtractSource:
    def test_extracts_domain_from_url(self):
        assert _extract_source("https://techcrunch.com/feed/") == "techcrunch.com"

    def test_handles_www_prefix(self):
        assert _extract_source("https://www.example.com/rss") == "www.example.com"

    def test_handles_subdomain(self):
        assert _extract_source("https://blog.openai.com/feed") == "blog.openai.com"


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

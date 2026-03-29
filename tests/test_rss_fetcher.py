"""Tests for RSS fetcher module."""

from datetime import datetime, timezone
from unittest.mock import patch

from ingest.rss_fetcher import _extract_source, _get_cutoff_time


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

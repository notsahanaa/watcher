"""Tests for RSS fetcher module."""

from ingest.rss_fetcher import _extract_source


class TestExtractSource:
    def test_extracts_domain_from_url(self):
        assert _extract_source("https://techcrunch.com/feed/") == "techcrunch.com"

    def test_handles_www_prefix(self):
        assert _extract_source("https://www.example.com/rss") == "www.example.com"

    def test_handles_subdomain(self):
        assert _extract_source("https://blog.openai.com/feed") == "blog.openai.com"

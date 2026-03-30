"""Tests for Slack delivery."""

import os
from unittest.mock import MagicMock, patch

import pytest

from deliver.slack import deliver_to_slack, format_digest_for_slack


@pytest.fixture
def sample_digest():
    """Sample digest for testing."""
    return {
        "top_highlights": [
            {
                "insight": "Claude 4 achieves breakthrough performance",
                "source": "techcrunch.com",
                "link": "https://techcrunch.com/article"
            }
        ],
        "themes": [
            {
                "name": "AI Developments",
                "subthemes": ["LLMs", "Agents"],
                "articles": [
                    {
                        "title": "New AI Framework Released",
                        "summary": "A new framework for building AI applications",
                        "link": "https://example.com/article"
                    }
                ]
            }
        ],
        "tools": {
            "new": [
                {
                    "name": "SuperTool",
                    "description": "Does amazing things",
                    "link": "https://supertool.com"
                }
            ],
            "updates": [
                {
                    "name": "ExistingTool",
                    "update": "Now supports Python 4",
                    "link": "https://existingtool.com"
                }
            ]
        },
        "skipped_count": 2,
        "skipped_reasons": ["duplicate", "irrelevant"]
    }


@pytest.fixture
def sample_summary():
    """Sample ingest summary for testing."""
    return {
        "total_feeds": 10,
        "successful": 8,
        "failed": 2,
        "articles_found": 45
    }


class TestFormatDigestForSlack:
    """Tests for format_digest_for_slack function."""

    def test_returns_blocks_payload(self, sample_digest, sample_summary):
        """Should return a payload with blocks array."""
        result = format_digest_for_slack(sample_digest, sample_summary)
        assert "blocks" in result
        assert isinstance(result["blocks"], list)
        assert len(result["blocks"]) > 0

    def test_includes_header(self, sample_digest, sample_summary):
        """Should include a header block."""
        result = format_digest_for_slack(sample_digest, sample_summary)
        header_blocks = [b for b in result["blocks"] if b.get("type") == "header"]
        assert len(header_blocks) == 1
        assert "WATCHER DAILY DIGEST" in header_blocks[0]["text"]["text"]

    def test_includes_highlights(self, sample_digest, sample_summary):
        """Should include highlights section."""
        result = format_digest_for_slack(sample_digest, sample_summary)
        blocks_text = str(result["blocks"])
        assert "TOP HIGHLIGHTS" in blocks_text
        assert "Claude 4 achieves breakthrough performance" in blocks_text

    def test_includes_themes(self, sample_digest, sample_summary):
        """Should include themes section."""
        result = format_digest_for_slack(sample_digest, sample_summary)
        blocks_text = str(result["blocks"])
        assert "THEMES" in blocks_text
        assert "AI Developments" in blocks_text
        assert "LLMs, Agents" in blocks_text

    def test_includes_tools(self, sample_digest, sample_summary):
        """Should include tools sections."""
        result = format_digest_for_slack(sample_digest, sample_summary)
        blocks_text = str(result["blocks"])
        assert "NEW TOOLS" in blocks_text
        assert "SuperTool" in blocks_text
        assert "TOOL UPDATES" in blocks_text
        assert "ExistingTool" in blocks_text

    def test_includes_footer_stats(self, sample_digest, sample_summary):
        """Should include footer with statistics."""
        result = format_digest_for_slack(sample_digest, sample_summary)
        blocks_text = str(result["blocks"])
        assert "8 feeds fetched" in blocks_text
        assert "45 articles processed" in blocks_text
        assert "2 skipped" in blocks_text

    def test_handles_empty_sections(self, sample_summary):
        """Should handle digest with empty sections."""
        empty_digest = {
            "top_highlights": [],
            "themes": [],
            "tools": {"new": [], "updates": []},
            "skipped_count": 0
        }
        result = format_digest_for_slack(empty_digest, sample_summary)
        assert "blocks" in result
        # Should still have header and footer
        assert len(result["blocks"]) >= 2

    def test_handles_missing_links(self, sample_summary):
        """Should handle items without links."""
        digest = {
            "top_highlights": [
                {"insight": "No link here", "source": "unknown"}
            ],
            "themes": [],
            "tools": {"new": [], "updates": []}
        }
        result = format_digest_for_slack(digest, sample_summary)
        blocks_text = str(result["blocks"])
        assert "No link here" in blocks_text
        assert "(unknown)" in blocks_text


class TestDeliverToSlack:
    """Tests for deliver_to_slack function."""

    def test_skips_when_no_webhook_url(self, sample_digest, sample_summary):
        """Should skip delivery when SLACK_WEBHOOK_URL is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove SLACK_WEBHOOK_URL if present
            os.environ.pop("SLACK_WEBHOOK_URL", None)
            success, error = deliver_to_slack(sample_digest, sample_summary)
            assert success is False
            assert error is None  # Not an error, just skipped

    def test_skips_when_no_digest(self, sample_summary):
        """Should skip delivery when digest is None or empty."""
        with patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}):
            success, error = deliver_to_slack(None, sample_summary)
            assert success is False
            assert error is None

            success, error = deliver_to_slack({}, sample_summary)
            assert success is False
            assert error is None

    @patch("deliver.slack.requests.post")
    def test_posts_to_webhook(self, mock_post, sample_digest, sample_summary):
        """Should POST to webhook URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        webhook_url = "https://hooks.slack.com/services/TEST/WEBHOOK"
        with patch.dict(os.environ, {"SLACK_WEBHOOK_URL": webhook_url}):
            success, error = deliver_to_slack(sample_digest, sample_summary)

            assert success is True
            assert error is None
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == webhook_url
            assert "blocks" in call_args[1]["json"]

    @patch("deliver.slack.requests.post")
    def test_handles_api_error(self, mock_post, sample_digest, sample_summary):
        """Should handle Slack API errors gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}):
            success, error = deliver_to_slack(sample_digest, sample_summary)

            assert success is False
            assert error is not None
            assert "500" in error

    @patch("deliver.slack.requests.post")
    def test_handles_request_exception(self, mock_post, sample_digest, sample_summary):
        """Should handle network errors gracefully."""
        import requests
        mock_post.side_effect = requests.RequestException("Connection refused")

        with patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}):
            success, error = deliver_to_slack(sample_digest, sample_summary)

            assert success is False
            assert error is not None
            assert "Connection refused" in error

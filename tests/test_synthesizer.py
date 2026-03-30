"""Tests for synthesizer module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from synthesize.synthesizer import (
    _build_prompt,
    _parse_response,
    synthesize,
)


class TestBuildPrompt:
    def test_includes_persona(self):
        articles = [{"title": "Test", "source": "test.com", "category": "AI",
                     "published": "2026-03-29", "link": "https://test.com/1",
                     "content": "Article content"}]
        prompt = _build_prompt(articles)
        # Should include something from the persona
        assert "AI Builder" in prompt or "PERSONA" in prompt or "digest" in prompt.lower()

    def test_includes_all_articles(self):
        articles = [
            {"title": "Article 1", "source": "a.com", "category": "AI",
             "published": "2026-03-29", "link": "https://a.com/1", "content": "Content 1"},
            {"title": "Article 2", "source": "b.com", "category": "Tech",
             "published": "2026-03-29", "link": "https://b.com/2", "content": "Content 2"},
        ]
        prompt = _build_prompt(articles)
        assert "Article 1" in prompt
        assert "Article 2" in prompt
        assert "a.com" in prompt
        assert "b.com" in prompt

    def test_falls_back_to_summary_if_no_content(self):
        articles = [{"title": "Test", "source": "test.com", "category": "AI",
                     "published": "2026-03-29", "link": "https://test.com/1",
                     "summary": "RSS summary here"}]
        prompt = _build_prompt(articles)
        assert "RSS summary here" in prompt


class TestParseResponse:
    def test_parses_valid_json(self):
        content = '{"top_highlights": [], "themes": [], "tools": {}}'
        result = _parse_response(content)
        assert result is not None
        assert "top_highlights" in result

    def test_extracts_json_from_markdown_code_block(self):
        content = '```json\n{"top_highlights": [], "themes": []}\n```'
        result = _parse_response(content)
        assert result is not None
        assert "top_highlights" in result

    def test_extracts_json_from_plain_code_block(self):
        content = '```\n{"top_highlights": [], "themes": []}\n```'
        result = _parse_response(content)
        assert result is not None
        assert "top_highlights" in result

    def test_returns_none_for_invalid_json(self):
        content = "This is not JSON at all"
        result = _parse_response(content)
        assert result is None

    def test_handles_complex_json(self):
        content = json.dumps({
            "top_highlights": [
                {"insight": "Key insight here", "source": "test.com", "link": "https://test.com/1"}
            ],
            "themes": [
                {"name": "AI Tools", "subthemes": ["LLMs", "Agents"], "articles": []}
            ],
            "tools": {
                "new": [{"name": "NewTool", "description": "Does things", "why_notable": "Important", "link": "url"}],
                "updates": []
            },
            "skipped_count": 2,
            "skipped_reasons": ["Funding news"]
        })
        result = _parse_response(content)
        assert result is not None
        assert len(result["top_highlights"]) == 1
        assert result["themes"][0]["name"] == "AI Tools"


class TestSynthesize:
    def test_returns_error_for_empty_articles(self):
        digest, error = synthesize([])
        assert digest is None
        assert "No articles" in error

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=True)
    def test_returns_error_if_no_api_key(self):
        articles = [{"title": "Test", "source": "test.com", "category": "AI",
                     "published": "2026-03-29", "link": "https://test.com/1",
                     "content": "Content"}]
        digest, error = synthesize(articles)
        assert digest is None
        assert "ANTHROPIC_API_KEY" in error

    @patch("synthesize.synthesizer.Anthropic")
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_calls_claude_api_with_articles(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "top_highlights": [],
            "themes": [],
            "tools": {"new": [], "updates": []},
            "skipped_count": 0,
            "skipped_reasons": []
        }))]
        mock_client.messages.create.return_value = mock_response

        articles = [{"title": "Test Article", "source": "test.com", "category": "AI",
                     "published": "2026-03-29", "link": "https://test.com/1",
                     "content": "Article content here"}]

        digest, error = synthesize(articles)

        assert error is None
        assert digest is not None
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args
        assert "claude-sonnet-4-20250514" in str(call_args)

    @patch("synthesize.synthesizer.Anthropic")
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_returns_parsed_digest(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        expected_digest = {
            "top_highlights": [
                {"insight": "Important finding", "source": "ai.com", "link": "https://ai.com/1"}
            ],
            "themes": [
                {"name": "AI Agents", "subthemes": ["Automation"], "articles": []}
            ],
            "tools": {
                "new": [{"name": "AgentKit", "description": "Build agents",
                         "why_notable": "Easy to use", "link": "https://agentkit.com"}],
                "updates": []
            },
            "skipped_count": 1,
            "skipped_reasons": ["Funding announcement"]
        }

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(expected_digest))]
        mock_client.messages.create.return_value = mock_response

        articles = [{"title": "Test", "source": "test.com", "category": "AI",
                     "published": "2026-03-29", "link": "https://test.com/1",
                     "content": "Content"}]

        digest, error = synthesize(articles)

        assert error is None
        assert digest == expected_digest

    @patch("synthesize.synthesizer.Anthropic")
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_handles_api_error(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API rate limit exceeded")

        articles = [{"title": "Test", "source": "test.com", "category": "AI",
                     "published": "2026-03-29", "link": "https://test.com/1",
                     "content": "Content"}]

        digest, error = synthesize(articles)

        assert digest is None
        assert "API rate limit" in error

    @patch("synthesize.synthesizer.Anthropic")
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_handles_invalid_json_response(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Not valid JSON response")]
        mock_client.messages.create.return_value = mock_response

        articles = [{"title": "Test", "source": "test.com", "category": "AI",
                     "published": "2026-03-29", "link": "https://test.com/1",
                     "content": "Content"}]

        digest, error = synthesize(articles)

        assert digest is None
        assert "Failed to parse" in error

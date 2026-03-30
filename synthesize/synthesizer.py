"""
Synthesizer module - processes articles with Claude API.

Takes articles from Stage 1 and produces a structured digest with:
- Top highlights (3-4 key insights)
- Themes (high-level themes with subthemes and use cases)
- Tools (new tools and updates to existing tools)
"""

import json
import logging
import os
from typing import Optional

from anthropic import Anthropic
from dotenv import load_dotenv

import config

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Claude model to use
MODEL = "claude-sonnet-4-20250514"


def _build_prompt(articles: list[dict]) -> str:
    """Build the prompt for Claude with articles and persona."""
    # Format articles for the prompt
    articles_text = ""
    for i, article in enumerate(articles, 1):
        articles_text += f"\n---\n"
        articles_text += f"**Article {i}:** {article['title']}\n"
        articles_text += f"**Source:** {article['source']} | **Category:** {article['category']}\n"
        articles_text += f"**Published:** {article['published']}\n"
        articles_text += f"**Link:** {article['link']}\n"
        articles_text += f"\n{article.get('content', article.get('summary', ''))}\n"

    prompt = f"""You are creating a daily digest based on the following persona:

{config.PERSONA}

Here are today's articles:
{articles_text}

---

Analyze these articles and create a structured digest. Return a JSON object with this exact structure:

{{
    "top_highlights": [
        {{
            "insight": "3-4 line summary of a key insight",
            "source": "source.com",
            "link": "article url"
        }}
    ],
    "themes": [
        {{
            "name": "Theme Name",
            "subthemes": ["subtheme1", "subtheme2"],
            "articles": [
                {{
                    "title": "Article title",
                    "summary": "1-2 sentence summary",
                    "use_case": "How this applies to an AI builder",
                    "link": "article url"
                }}
            ]
        }}
    ],
    "tools": {{
        "new": [
            {{
                "name": "Tool Name",
                "description": "What it does",
                "why_notable": "Why an AI builder should care",
                "link": "article url"
            }}
        ],
        "updates": [
            {{
                "name": "Tool Name",
                "update": "What changed",
                "why_notable": "Why this update matters",
                "link": "article url"
            }}
        ]
    }},
    "skipped_count": 0,
    "skipped_reasons": ["List of reasons articles were skipped per persona guidelines"]
}}

Guidelines:
- top_highlights: 2-4 most important insights for an AI builder
- themes: Group related articles into coherent themes
- tools.new: Brand new tools mentioned in articles
- tools.updates: Updates to existing tools that unlock new possibilities
- Skip articles that don't match the persona (funding news, ethics debates, repetitive coverage)
- Be concise but specific
- Every insight should be actionable

Return ONLY valid JSON, no markdown code blocks or extra text."""

    return prompt


def _parse_response(content: str) -> Optional[dict]:
    """Parse Claude's response as JSON."""
    try:
        # Try to parse directly
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end > start:
                try:
                    return json.loads(content[start:end].strip())
                except json.JSONDecodeError:
                    pass
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end > start:
                try:
                    return json.loads(content[start:end].strip())
                except json.JSONDecodeError:
                    pass

        logger.error(f"Failed to parse Claude response as JSON: {content[:200]}...")
        return None


def synthesize(articles: list[dict]) -> tuple[Optional[dict], Optional[str]]:
    """
    Send articles to Claude API and get structured digest.

    Args:
        articles: List of article dicts from Stage 1

    Returns:
        Tuple of (digest dict, error message or None)
    """
    if not articles:
        logger.warning("No articles to synthesize")
        return None, "No articles provided"

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return None, "ANTHROPIC_API_KEY environment variable not set"

    try:
        client = Anthropic(api_key=api_key)
        prompt = _build_prompt(articles)

        logger.info(f"Sending {len(articles)} articles to Claude ({MODEL})...")

        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Extract text from response
        content = response.content[0].text

        # Parse JSON response
        digest = _parse_response(content)
        if digest is None:
            return None, "Failed to parse Claude response as JSON"

        logger.info(
            f"Synthesis complete: {len(digest.get('top_highlights', []))} highlights, "
            f"{len(digest.get('themes', []))} themes, "
            f"{len(digest.get('tools', {}).get('new', []))} new tools, "
            f"{len(digest.get('tools', {}).get('updates', []))} tool updates"
        )

        return digest, None

    except Exception as e:
        error_msg = f"Claude API error: {e}"
        logger.error(error_msg)
        return None, error_msg

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
    persona = config.ACTIVE_PERSONA

    # Format articles for the prompt
    articles_text = ""
    for i, article in enumerate(articles, 1):
        articles_text += f"\n---\n"
        articles_text += f"**Article {i}:** {article['title']}\n"
        articles_text += f"**Source:** {article['source']} | **Category:** {article['category']}\n"
        articles_text += f"**Published:** {article['published']}\n"
        articles_text += f"**Link:** {article['link']}\n"
        articles_text += f"\n{article.get('content', article.get('summary', ''))}\n"

    # Build persona description for the prompt
    persona_text = f"""Name: {persona['name']}
Description: {persona['description']}
Focus: {persona['framing']}
Skip these topics: {', '.join(persona['skip'])}"""

    prompt = f"""You are creating a daily digest based on the following persona:

{persona_text}

Here are today's articles:
{articles_text}

---

Your task is to SYNTHESIZE these articles into an insight-driven digest. Do NOT list articles individually - instead, identify patterns, merge related coverage, and surface what matters.

## Section 1: Top Highlights

Top highlights surface the IDEAS that multiple sources are talking about. This is how you identify them:

1. Read through all articles and identify recurring ideas, trends, or topics
2. Count how many DIFFERENT articles mention each idea
3. An idea qualifies as a "top highlight" ONLY if it appears in 3 or more articles
4. Select the top 3-4 qualifying ideas, ranked by how many articles mention them

For each top highlight, write a 2-3 sentence synthesis that captures the idea and why it matters.

## Section 2: Themes

Themes group related articles by the INSIGHT they share, not by category.

**Theme Headers - BE the takeaway, not a category:**
- BAD: "AI Development Tools" (this is a category label)
- BAD: "Model Updates" (too generic)
- GOOD: "The cost/performance war is heating up" (this is an insight)
- GOOD: "Cursor and OpenAI are racing to make frontier models affordable" (specific takeaway)

**Theme Body - Write ONE synthesized paragraph per theme (3-5 sentences):**
- Merge the key information from all related articles into coherent analysis
- Explain WHY this matters (the "so what" - why should the reader care?)
- Use inline citations: "...at a fraction of the cost (Cursor blog, OpenAI)."
- This should NOT read as a list of article summaries - it should read as original analysis

## Section 3: Tools

Extract any tools mentioned in the articles. For each tool:

**New Tools:**
- Name of the tool
- Summary: What it does (1-2 sentences - be specific, not generic)
- Comparison: How it compares to existing tools or alternatives (if applicable)
- Why it matters: What problem does it solve? Why should someone try it?

**Tool Updates:**
- Name of the tool
- Summary: What changed (be specific about the update)
- Comparison: How this update positions the tool vs alternatives (if applicable)
- Why it matters: What can you do now that you couldn't before?

## Section 4: Case Studies

Extract any examples of things people have built or shipped. These are valuable because they show real-world applications.

For each case study:
- What they built: The product, feature, or project
- How it works: The approach, tech stack, or methodology (if mentioned)
- Takeaway: What can you learn from this? What's the applicable insight?

If no case studies are mentioned in the articles, return an empty array.

## Output Format

Return a JSON object with this exact structure:

{{
  "top_highlights": [
    {{
      "insight": "A 2-3 sentence synthesis of an idea mentioned in 3+ articles",
      "sources": [
        {{"name": "Short source name", "link": "article url"}}
      ]
    }}
  ],
  "themes": [
    {{
      "takeaway": "The insight as a headline - a complete thought, not a category label",
      "synthesis": "A synthesized paragraph (3-5 sentences) that merges related articles, explains why this matters, and uses inline citations like (Source Name).",
      "sources": [
        {{"name": "Source Name", "link": "url"}}
      ]
    }}
  ],
  "tools": {{
    "new": [
      {{
        "name": "Tool Name",
        "summary": "What it does (1-2 sentences, specific)",
        "comparison": "How it compares to existing tools (if applicable)",
        "why_it_matters": "What problem it solves, why someone should try it",
        "link": "article url"
      }}
    ],
    "updates": [
      {{
        "name": "Tool Name",
        "summary": "What specifically changed",
        "comparison": "How this positions the tool vs alternatives (if applicable)",
        "why_it_matters": "What you can do now that you couldn't before",
        "link": "article url"
      }}
    ]
  }},
  "case_studies": [
    {{
      "what_they_built": "The product, feature, or project",
      "how_it_works": "The approach or methodology",
      "takeaway": "What you can learn from this",
      "link": "article url"
    }}
  ]
}}

## Guidelines

- top_highlights: Only include ideas that appear in 3+ articles. Empty array if no ideas meet this threshold.
- themes: 2-4 themed sections with synthesized paragraphs (not article lists)
- tools: Be specific. "AI coding tool" is bad. "VS Code extension that auto-completes entire functions using GPT-4" is good. Include comparisons when relevant alternatives exist.
- case_studies: Real examples of things people built. Skip if none mentioned.
- Every insight should answer "why should I care about this?"

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
            f"{len(digest.get('tools', {}).get('updates', []))} tool updates, "
            f"{len(digest.get('case_studies', []))} case studies"
        )

        return digest, None

    except Exception as e:
        error_msg = f"Claude API error: {e}"
        logger.error(error_msg)
        return None, error_msg

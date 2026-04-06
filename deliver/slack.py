"""Slack delivery for Watcher digests."""

import logging
import os
from datetime import datetime
from typing import Optional, Tuple

import requests

logger = logging.getLogger(__name__)


def format_digest_for_slack(digest: dict, summary: dict) -> dict:
    """
    Convert digest to Slack Block Kit format.

    Args:
        digest: The synthesized digest from Claude
        summary: The ingest summary with feed statistics

    Returns:
        Slack message payload with blocks
    """
    blocks = []

    # Header
    today = datetime.now().strftime("%B %d, %Y")
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": "📰 WATCHER DAILY DIGEST",
            "emoji": True
        }
    })
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"_{today}_"}]
    })
    blocks.append({"type": "divider"})

    # Top Highlights
    if digest.get("top_highlights"):
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*TOP HIGHLIGHTS*"}
        })
        for highlight in digest["top_highlights"]:
            insight = highlight.get("insight", "")
            sources = highlight.get("sources", [])
            # Build inline source links
            if sources:
                source_links = ", ".join(
                    f"<{s['link']}|{s['name']}>" if s.get("link") else s.get("name", "")
                    for s in sources
                )
                text = f"• {insight} ({source_links})"
            else:
                text = f"• {insight}"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": text}
            })
        blocks.append({"type": "divider"})

    # Themes
    if digest.get("themes"):
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*THEMES*"}
        })
        for theme in digest["themes"]:
            # Takeaway as the header (insight, not category)
            takeaway = theme.get("takeaway", "")
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{takeaway}*"}
            })
            # Synthesized paragraph
            synthesis = theme.get("synthesis", "")
            if synthesis:
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": synthesis}
                })
            # Source links
            sources = theme.get("sources", [])
            if sources:
                source_links = " | ".join(
                    f"<{s['link']}|{s['name']}>" if s.get("link") else s.get("name", "")
                    for s in sources
                )
                blocks.append({
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": f"Sources: {source_links}"}]
                })
        blocks.append({"type": "divider"})

    # Tools
    tools = digest.get("tools", {})
    if tools.get("new"):
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*NEW TOOLS*"}
        })
        for tool in tools["new"]:
            name = tool.get("name", "")
            tool_summary = tool.get("summary", tool.get("description", ""))  # fallback to description
            comparison = tool.get("comparison", "")
            why_it_matters = tool.get("why_it_matters", "")
            link = tool.get("link", "")
            # Build tool text with summary, comparison, and why it matters
            tool_text = f"• *{name}*"
            if tool_summary:
                tool_text += f" - {tool_summary}"
            if comparison:
                tool_text += f"\n  _vs alternatives: {comparison}_"
            if why_it_matters:
                tool_text += f"\n  _Why it matters: {why_it_matters}_"
            if link:
                tool_text += f" (<{link}|Link>)"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": tool_text}
            })

    if tools.get("updates"):
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*TOOL UPDATES*"}
        })
        for tool in tools["updates"]:
            name = tool.get("name", "")
            tool_summary = tool.get("summary", tool.get("update", ""))  # fallback to update
            comparison = tool.get("comparison", "")
            why_it_matters = tool.get("why_it_matters", "")
            link = tool.get("link", "")
            # Build tool text with summary, comparison, and why it matters
            tool_text = f"• *{name}*"
            if tool_summary:
                tool_text += f" - {tool_summary}"
            if comparison:
                tool_text += f"\n  _vs alternatives: {comparison}_"
            if why_it_matters:
                tool_text += f"\n  _Why it matters: {why_it_matters}_"
            if link:
                tool_text += f" (<{link}|Link>)"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": tool_text}
            })

    # Case Studies
    case_studies = digest.get("case_studies", [])
    if case_studies:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*CASE STUDIES*"}
        })
        for case in case_studies:
            what_built = case.get("what_they_built", "")
            how_works = case.get("how_it_works", "")
            takeaway = case.get("takeaway", "")
            link = case.get("link", "")
            # Build case study text
            case_text = f"• *{what_built}*"
            if how_works:
                case_text += f"\n  How it works: {how_works}"
            if takeaway:
                case_text += f"\n  _Takeaway: {takeaway}_"
            if link:
                case_text += f" (<{link}|Link>)"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": case_text}
            })

    # Footer with stats
    blocks.append({"type": "divider"})
    stats_parts = []
    if summary.get("successful") is not None:
        stats_parts.append(f"{summary['successful']} feeds fetched")
    if summary.get("articles_found") is not None:
        stats_parts.append(f"{summary['articles_found']} articles processed")
    if digest.get("skipped_count", 0) > 0:
        stats_parts.append(f"{digest['skipped_count']} skipped")

    stats_text = ", ".join(stats_parts) if stats_parts else "Digest complete"
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"_{stats_text}_"}]
    })

    return {"blocks": blocks}


def deliver_to_slack(digest: dict, summary: dict) -> Tuple[bool, Optional[str]]:
    """
    Post digest to Slack webhook.

    Args:
        digest: The synthesized digest from Claude
        summary: The ingest summary with feed statistics

    Returns:
        Tuple of (success: bool, error_message: str | None)
    """
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")

    if not webhook_url:
        logger.info("SLACK_WEBHOOK_URL not set, skipping Slack delivery")
        return False, None

    if not digest:
        logger.info("No digest to deliver to Slack")
        return False, None

    try:
        payload = format_digest_for_slack(digest, summary)
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            logger.info("Successfully posted digest to Slack")
            return True, None
        else:
            error_msg = f"Slack API returned {response.status_code}: {response.text}"
            logger.warning(error_msg)
            return False, error_msg

    except requests.RequestException as e:
        error_msg = f"Failed to post to Slack: {str(e)}"
        logger.warning(error_msg)
        return False, error_msg

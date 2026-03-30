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
            source = highlight.get("source", "")
            link = highlight.get("link", "")
            insight = highlight.get("insight", "")
            if link:
                text = f"• {insight} (<{link}|{source}>)"
            else:
                text = f"• {insight} ({source})"
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
            subthemes = ", ".join(theme.get("subthemes", []))
            theme_text = f"*{theme['name']}*"
            if subthemes:
                theme_text += f" - {subthemes}"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": theme_text}
            })
            for article in theme.get("articles", []):
                title = article.get("title", "")
                article_summary = article.get("summary", "")
                link = article.get("link", "")
                if link:
                    article_text = f"  • {title} - {article_summary} (<{link}|Read more>)"
                else:
                    article_text = f"  • {title} - {article_summary}"
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": article_text}
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
            description = tool.get("description", "")
            link = tool.get("link", "")
            if link:
                text = f"• *{name}* - {description} (<{link}|Link>)"
            else:
                text = f"• *{name}* - {description}"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": text}
            })

    if tools.get("updates"):
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*TOOL UPDATES*"}
        })
        for tool in tools["updates"]:
            name = tool.get("name", "")
            update = tool.get("update", "")
            link = tool.get("link", "")
            if link:
                text = f"• *{name}* - {update} (<{link}|Link>)"
            else:
                text = f"• *{name}* - {update}"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": text}
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

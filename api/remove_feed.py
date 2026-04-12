"""
Vercel serverless function to remove RSS feeds via Slack slash command.

Handles /watcher-remove-feed slash command:
- Verifies Slack request signature
- Parses feed URL from command
- Removes feed from feeds.json in GitHub repo via API
- Returns confirmation message to Slack
"""

import base64
import hashlib
import hmac
import json
import os
import time

import requests
from flask import Flask, request, jsonify


# Environment variables (set in Vercel dashboard)
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # Format: "owner/repo"

# GitHub API base URL
GITHUB_API_BASE = "https://api.github.com"

app = Flask(__name__)


def verify_slack_signature(body: bytes, timestamp: str, signature: str) -> bool:
    """
    Verify that the request came from Slack using signing secret.

    See: https://api.slack.com/authentication/verifying-requests-from-slack
    """
    if not SLACK_SIGNING_SECRET:
        return False

    # Validate timestamp exists
    if not timestamp:
        return False

    # Check timestamp to prevent replay attacks (allow 5 min window)
    try:
        if abs(time.time() - int(timestamp)) > 60 * 5:
            return False
    except ValueError:
        return False

    # Compute expected signature
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    expected_sig = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_sig, signature)


def get_feeds_from_github() -> tuple[dict, str]:
    """
    Fetch current feeds.json from GitHub.

    Returns:
        Tuple of (feeds dict, file SHA for updates)
    """
    url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/contents/feeds.json"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    data = response.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    feeds = json.loads(content)

    return feeds, data["sha"]


def update_feeds_on_github(feeds: dict, sha: str, feed_url: str) -> None:
    """
    Update feeds.json on GitHub with new content.

    Args:
        feeds: Updated feeds dictionary
        sha: Current file SHA (required for updates)
        feed_url: The feed URL being removed (for commit message)
    """
    url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/contents/feeds.json"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    content = json.dumps(feeds, indent=2) + "\n"
    encoded_content = base64.b64encode(content.encode()).decode()

    payload = {
        "message": f"Remove feed: {feed_url}",
        "content": encoded_content,
        "sha": sha,
    }

    response = requests.put(url, headers=headers, json=payload)
    response.raise_for_status()


def parse_command(text: str) -> str:
    """
    Parse slash command text to extract feed URL.

    Format: /watcher-remove-feed <url>

    Returns:
        feed_url
    """
    feed_url = text.strip()

    if not feed_url:
        raise ValueError("No feed URL provided")

    # Basic URL validation
    if not feed_url.startswith(("http://", "https://")):
        raise ValueError(f"Invalid URL: {feed_url}")

    return feed_url


def remove_feed(feed_url: str) -> str:
    """
    Remove a feed URL from feeds.json.

    Searches all categories for the feed and removes it if found.

    Returns:
        Success or not-found message
    """
    feeds, sha = get_feeds_from_github()

    # Search all categories for the feed
    for category, urls in feeds.items():
        if feed_url in urls:
            urls.remove(feed_url)
            update_feeds_on_github(feeds, sha, feed_url)
            return f"Removed feed from {category}: {feed_url}"

    # Feed not found - build helpful message with current feeds
    all_feeds = []
    for category, urls in feeds.items():
        for url in urls:
            all_feeds.append(f"* {url} ({category})")

    if all_feeds:
        feeds_list = "\n".join(all_feeds)
        return f"Feed not found: {feed_url}\n\n*Currently tracked feeds:*\n{feeds_list}"
    else:
        return f"Feed not found: {feed_url}\n\nNo feeds are currently being tracked."


@app.route("/api/remove_feed", methods=["POST"])
def handle_remove_feed():
    """Handle POST request from Slack slash command."""
    try:
        # Get raw body for signature verification
        body = request.get_data()

        # Verify Slack signature
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")

        if not verify_slack_signature(body, timestamp, signature):
            return jsonify({
                "response_type": "ephemeral",
                "text": "Invalid signature"
            }), 401

        # Parse form data
        command_text = request.form.get("text", "")

        # Parse and remove feed
        feed_url = parse_command(command_text)
        message = remove_feed(feed_url)

        # Determine response icon based on result
        if message.startswith("Feed not found"):
            icon = ":warning:"
        else:
            icon = ":white_check_mark:"

        return jsonify({
            "response_type": "in_channel",
            "text": f"{icon} {message}"
        })

    except ValueError as e:
        # User error (bad input)
        return jsonify({
            "response_type": "ephemeral",
            "text": f":x: Error: {str(e)}\n\nUsage: `/watcher-remove-feed <feed-url>`"
        })

    except Exception as e:
        # Server error
        return jsonify({
            "response_type": "ephemeral",
            "text": f":x: Something went wrong: {str(e)}"
        })

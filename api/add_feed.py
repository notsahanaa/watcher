"""
Vercel serverless function to add RSS feeds via Slack slash command.

Handles /watcher-add slash command:
- Verifies Slack request signature
- Parses feed URL (and optional category) from command
- Updates feeds.json in GitHub repo via API
- Returns confirmation message to Slack
"""

import base64
import hashlib
import hmac
import json
import os
import time
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

import requests


# Environment variables (set in Vercel dashboard)
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # Format: "owner/repo"

# GitHub API base URL
GITHUB_API_BASE = "https://api.github.com"

# Default category for new feeds
DEFAULT_CATEGORY = "AI Tools"


def verify_slack_signature(
    body: bytes, timestamp: str, signature: str
) -> bool:
    """
    Verify that the request came from Slack using signing secret.

    See: https://api.slack.com/authentication/verifying-requests-from-slack
    """
    if not SLACK_SIGNING_SECRET:
        return False

    # Check timestamp to prevent replay attacks (allow 5 min window)
    if abs(time.time() - int(timestamp)) > 60 * 5:
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
        feed_url: The feed URL being added (for commit message)
    """
    url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/contents/feeds.json"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    content = json.dumps(feeds, indent=2) + "\n"
    encoded_content = base64.b64encode(content.encode()).decode()

    payload = {
        "message": f"Add feed: {feed_url}",
        "content": encoded_content,
        "sha": sha,
    }

    response = requests.put(url, headers=headers, json=payload)
    response.raise_for_status()


def parse_command(text: str) -> tuple[str, str]:
    """
    Parse slash command text into feed URL and category.

    Format: /watcher-add <url> [category]

    Returns:
        Tuple of (feed_url, category)
    """
    parts = text.strip().split(maxsplit=1)

    if not parts:
        raise ValueError("No feed URL provided")

    feed_url = parts[0]

    # Basic URL validation
    if not feed_url.startswith(("http://", "https://")):
        raise ValueError(f"Invalid URL: {feed_url}")

    # Category is optional, defaults to DEFAULT_CATEGORY
    category = parts[1] if len(parts) > 1 else DEFAULT_CATEGORY

    return feed_url, category


def add_feed(feed_url: str, category: str) -> str:
    """
    Add a feed URL to the specified category in feeds.json.

    Returns:
        Success message
    """
    # Get current feeds
    feeds, sha = get_feeds_from_github()

    # Ensure category exists
    if category not in feeds:
        feeds[category] = []

    # Check if feed already exists
    if feed_url in feeds[category]:
        return f"Feed already exists in {category}: {feed_url}"

    # Add feed
    feeds[category].append(feed_url)

    # Update on GitHub
    update_feeds_on_github(feeds, sha, feed_url)

    return f"Added feed to {category}: {feed_url}"


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""

    def do_POST(self):
        """Handle POST request from Slack slash command."""
        try:
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            # Verify Slack signature
            timestamp = self.headers.get("X-Slack-Request-Timestamp", "")
            signature = self.headers.get("X-Slack-Signature", "")

            if not verify_slack_signature(body, timestamp, signature):
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid signature"}).encode())
                return

            # Parse form data
            form_data = parse_qs(body.decode("utf-8"))
            command_text = form_data.get("text", [""])[0]

            # Parse and add feed
            feed_url, category = parse_command(command_text)
            message = add_feed(feed_url, category)

            # Send success response to Slack
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            response = {
                "response_type": "in_channel",
                "text": f":white_check_mark: {message}"
            }
            self.wfile.write(json.dumps(response).encode())

        except ValueError as e:
            # User error (bad input)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            response = {
                "response_type": "ephemeral",
                "text": f":x: Error: {str(e)}\n\nUsage: `/watcher-add <feed-url> [category]`"
            }
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            # Server error
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            response = {
                "response_type": "ephemeral",
                "text": f":x: Something went wrong: {str(e)}"
            }
            self.wfile.write(json.dumps(response).encode())

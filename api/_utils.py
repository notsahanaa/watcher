"""
Shared utilities for Vercel serverless functions.

Underscore prefix prevents Vercel from routing to this as an endpoint.
"""

import base64
import hashlib
import hmac
import json
import os
import time

import requests


# Environment variables (set in Vercel dashboard)
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # Format: "owner/repo"

# GitHub API base URL
GITHUB_API_BASE = "https://api.github.com"


def verify_slack_signature(body: bytes, timestamp: str, signature: str) -> bool:
    """
    Verify that the request came from Slack using signing secret.

    See: https://api.slack.com/authentication/verifying-requests-from-slack
    """
    if not SLACK_SIGNING_SECRET:
        return False

    # Check timestamp to prevent replay attacks (allow 5 min window)
    try:
        if abs(time.time() - int(timestamp)) > 60 * 5:
            return False
    except (ValueError, TypeError):
        return False

    # Compute expected signature
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    expected_sig = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_sig, signature)


def get_file_from_github(filename: str) -> tuple[dict | None, str | None]:
    """
    Fetch a JSON file from GitHub.

    Args:
        filename: Name of the file (e.g., "feeds.json", "state.json")

    Returns:
        Tuple of (content dict, file SHA) or (None, None) if file doesn't exist
    """
    url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/contents/{filename}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 404:
        return None, None

    response.raise_for_status()

    data = response.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    parsed = json.loads(content)

    return parsed, data["sha"]


def update_file_on_github(
    filename: str,
    content: dict,
    sha: str | None,
    message: str
) -> None:
    """
    Create or update a JSON file on GitHub.

    Args:
        filename: Name of the file (e.g., "feeds.json", "state.json")
        content: Dictionary to save as JSON
        sha: Current file SHA (required for updates, None for new files)
        message: Commit message
    """
    url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/contents/{filename}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    json_content = json.dumps(content, indent=2) + "\n"
    encoded_content = base64.b64encode(json_content.encode()).decode()

    payload = {
        "message": message,
        "content": encoded_content,
    }

    if sha:
        payload["sha"] = sha

    response = requests.put(url, headers=headers, json=payload)
    response.raise_for_status()


def send_slack_response(
    handler,
    status: int,
    response_type: str,
    text: str
) -> None:
    """
    Send a formatted response to Slack.

    Args:
        handler: BaseHTTPRequestHandler instance
        status: HTTP status code
        response_type: "in_channel" or "ephemeral"
        text: Message text (supports Slack emoji like :white_check_mark:)
    """
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.end_headers()

    response = {
        "response_type": response_type,
        "text": text
    }
    handler.wfile.write(json.dumps(response).encode())

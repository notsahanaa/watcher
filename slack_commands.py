"""
Modal serverless functions for Slack slash commands.

Handles all Watcher slash commands:
- /watcher-add-feed: Add an RSS feed to track
- /watcher-remove-feed: Remove a tracked feed
- /watcher-pause: Pause daily digests
- /watcher-unpause: Resume daily digests

Each endpoint verifies Slack signatures and updates GitHub via API.
Uses FastAPI endpoints for native UTF-8 support.
Uses Modal spawn for deferred responses to handle cold starts.
"""

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict

import modal
import requests
from fastapi import Request, Response

# Modal app with dependencies
image = modal.Image.debian_slim().pip_install("requests", "fastapi", "python-multipart")
app = modal.App("watcher-slack-commands", image=image)

# Secrets from Modal
secrets = modal.Secret.from_name("watcher-secrets")

# GitHub API base URL
GITHUB_API_BASE = "https://api.github.com"

# Default category for new feeds
DEFAULT_CATEGORY = "AI Tools"

# Default state when state.json doesn't exist
DEFAULT_STATE = {
    "paused": False,
    "paused_at": None,
    "paused_by": None,
}


def verify_slack_signature(
    body: bytes,
    timestamp: str,
    signature: str,
    signing_secret: str
) -> bool:
    """
    Verify that the request came from Slack using signing secret.
    """
    if not signing_secret:
        return False

    try:
        if abs(time.time() - int(timestamp)) > 60 * 5:
            return False
    except (ValueError, TypeError):
        return False

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    expected_sig = "v0=" + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_sig, signature)


def get_file_from_github(
    filename: str,
    github_token: str,
    github_repo: str
) -> Tuple[Optional[Dict], Optional[str]]:
    """Fetch a JSON file from GitHub."""
    url = f"{GITHUB_API_BASE}/repos/{github_repo}/contents/{filename}"
    headers = {
        "Authorization": f"Bearer {github_token}",
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
    sha: Optional[str],
    message: str,
    github_token: str,
    github_repo: str
) -> None:
    """Create or update a JSON file on GitHub."""
    url = f"{GITHUB_API_BASE}/repos/{github_repo}/contents/{filename}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json; charset=utf-8",
    }

    json_content = json.dumps(content, indent=2) + "\n"
    encoded_content = base64.b64encode(json_content.encode("utf-8")).decode("ascii")

    payload = {
        "message": message,
        "content": encoded_content,
    }

    if sha:
        payload["sha"] = sha

    # Explicitly encode as UTF-8 bytes
    data = json.dumps(payload).encode("utf-8")
    response = requests.put(url, headers=headers, data=data)
    response.raise_for_status()


def sanitize_string(s: str) -> str:
    """Remove any non-ASCII characters that could cause encoding issues."""
    if not s:
        return s
    # Encode to ASCII, ignoring non-ASCII chars, then decode back
    return s.encode('ascii', 'ignore').decode('ascii')


def send_slack_response(response_url: str, response_type: str, text: str) -> None:
    """Send a deferred response to Slack via response_url."""
    # Sanitize inputs to avoid encoding issues
    clean_url = sanitize_string(response_url)
    clean_text = sanitize_string(text)

    payload = {"response_type": response_type, "text": clean_text}

    # Use json= parameter which handles encoding correctly
    requests.post(clean_url, json=payload)


# Background worker functions (spawned by endpoints)

@app.function(secrets=[secrets])
def do_add_feed(response_url: str, command_text: str) -> None:
    """Background task to add a feed and respond to Slack."""
    import os
    github_token = sanitize_string(os.environ["GITHUB_TOKEN"])
    github_repo = sanitize_string(os.environ["GITHUB_REPO"])

    # Debug logging for inputs
    print(f"[DEBUG] do_add_feed called")
    print(f"[DEBUG] response_url repr: {repr(response_url)}")
    print(f"[DEBUG] command_text repr: {repr(command_text)}")

    # Sanitize inputs
    response_url = sanitize_string(response_url)
    command_text = sanitize_string(command_text)

    print(f"[DEBUG] sanitized response_url: {repr(response_url)}")
    print(f"[DEBUG] sanitized command_text: {repr(command_text)}")

    try:
        parts = command_text.strip().split(maxsplit=1)

        if not parts:
            send_slack_response(
                response_url, "ephemeral",
                ":x: Error: No feed URL provided\n\nUsage: `/watcher-add-feed <feed-url> [category]`"
            )
            return

        feed_url = parts[0]

        if not feed_url.startswith(("http://", "https://")):
            send_slack_response(
                response_url, "ephemeral",
                f":x: Error: Invalid URL: {feed_url}\n\nUsage: `/watcher-add-feed <feed-url> [category]`"
            )
            return

        category = parts[1] if len(parts) > 1 else DEFAULT_CATEGORY

        feeds, sha = get_file_from_github("feeds.json", github_token, github_repo)

        if feeds is None:
            feeds = {}
            sha = None

        if category not in feeds:
            feeds[category] = []

        if feed_url in feeds[category]:
            send_slack_response(
                response_url, "in_channel",
                f":information_source: Feed already exists in {category}: {feed_url}"
            )
            return

        feeds[category].append(feed_url)

        update_file_on_github(
            "feeds.json", feeds, sha,
            f"Add feed: {feed_url}",
            github_token, github_repo
        )

        send_slack_response(
            response_url, "in_channel",
            f":white_check_mark: Added feed to {category}: {feed_url}"
        )

    except Exception as e:
        send_slack_response(response_url, "ephemeral", f":x: Something went wrong: {str(e)}")


@app.function(secrets=[secrets])
def do_remove_feed(response_url: str, feed_url: str) -> None:
    """Background task to remove a feed and respond to Slack."""
    import os
    github_token = sanitize_string(os.environ["GITHUB_TOKEN"])
    github_repo = sanitize_string(os.environ["GITHUB_REPO"])

    # Sanitize inputs
    response_url = sanitize_string(response_url)
    feed_url = sanitize_string(feed_url)

    try:
        if not feed_url:
            send_slack_response(
                response_url, "ephemeral",
                ":x: Error: No feed URL provided\n\nUsage: `/watcher-remove-feed <feed-url>`"
            )
            return

        if not feed_url.startswith(("http://", "https://")):
            send_slack_response(
                response_url, "ephemeral",
                f":x: Error: Invalid URL: {feed_url}\n\nUsage: `/watcher-remove-feed <feed-url>`"
            )
            return

        feeds, sha = get_file_from_github("feeds.json", github_token, github_repo)

        if feeds is None:
            send_slack_response(
                response_url, "ephemeral",
                f":warning: Feed not found: {feed_url}\n\nNo feeds are currently being tracked."
            )
            return

        for category, urls in feeds.items():
            if feed_url in urls:
                urls.remove(feed_url)
                update_file_on_github(
                    "feeds.json", feeds, sha,
                    f"Remove feed: {feed_url}",
                    github_token, github_repo
                )
                send_slack_response(
                    response_url, "in_channel",
                    f":white_check_mark: Removed feed from {category}: {feed_url}"
                )
                return

        all_feeds = []
        for category, urls in feeds.items():
            for url in urls:
                all_feeds.append(f"• {url} ({category})")

        if all_feeds:
            feeds_list = "\n".join(all_feeds)
            send_slack_response(
                response_url, "ephemeral",
                f":warning: Feed not found: {feed_url}\n\n*Currently tracked feeds:*\n{feeds_list}"
            )
        else:
            send_slack_response(
                response_url, "ephemeral",
                f":warning: Feed not found: {feed_url}\n\nNo feeds are currently being tracked."
            )

    except Exception as e:
        send_slack_response(response_url, "ephemeral", f":x: Something went wrong: {str(e)}")


@app.function(secrets=[secrets])
def do_pause(response_url: str, user_name: str) -> None:
    """Background task to pause watcher and respond to Slack."""
    import os
    github_token = sanitize_string(os.environ["GITHUB_TOKEN"])
    github_repo = sanitize_string(os.environ["GITHUB_REPO"])

    # Sanitize inputs
    response_url = sanitize_string(response_url)
    user_name = sanitize_string(user_name)

    try:
        state, sha = get_file_from_github("state.json", github_token, github_repo)

        if state is None:
            state = DEFAULT_STATE.copy()

        if state.get("paused", False):
            paused_by = state.get("paused_by", "someone")
            paused_at = state.get("paused_at", "unknown time")
            send_slack_response(
                response_url, "ephemeral",
                f":pause_button: Watcher is already paused (by {paused_by} at {paused_at})"
            )
            return

        state["paused"] = True
        state["paused_at"] = datetime.now(timezone.utc).isoformat()
        state["paused_by"] = user_name

        update_file_on_github(
            "state.json", state, sha,
            f"Pause watcher (by {user_name})",
            github_token, github_repo
        )

        send_slack_response(
            response_url, "in_channel",
            f":pause_button: Watcher paused by @{user_name}. Use `/watcher-unpause` to resume."
        )

    except Exception as e:
        send_slack_response(response_url, "ephemeral", f":x: Something went wrong: {str(e)}")


@app.function(secrets=[secrets])
def do_unpause(response_url: str, user_name: str) -> None:
    """Background task to unpause watcher and respond to Slack."""
    import os
    github_token = sanitize_string(os.environ["GITHUB_TOKEN"])
    github_repo = sanitize_string(os.environ["GITHUB_REPO"])

    # Sanitize inputs
    response_url = sanitize_string(response_url)
    user_name = sanitize_string(user_name)

    try:
        state, sha = get_file_from_github("state.json", github_token, github_repo)

        if state is None or not state.get("paused", False):
            send_slack_response(
                response_url, "ephemeral",
                ":arrow_forward: Watcher is already running!"
            )
            return

        state["paused"] = False
        state["paused_at"] = None
        state["paused_by"] = None

        update_file_on_github(
            "state.json", state, sha,
            f"Unpause watcher (by {user_name})",
            github_token, github_repo
        )

        send_slack_response(
            response_url, "in_channel",
            f":arrow_forward: Watcher resumed by @{user_name}. Daily digests will continue."
        )

    except Exception as e:
        send_slack_response(response_url, "ephemeral", f":x: Something went wrong: {str(e)}")


# HTTP Endpoints (respond immediately, spawn background work)

@app.function(secrets=[secrets], min_containers=1)
@modal.fastapi_endpoint(method="POST")
async def add_feed(request: Request) -> Response:
    """Handle /watcher-add-feed slash command."""
    import os

    signing_secret = os.environ["SLACK_SIGNING_SECRET"]

    body = await request.body()
    timestamp = request.headers.get("x-slack-request-timestamp", "")
    signature = request.headers.get("x-slack-signature", "")

    if not verify_slack_signature(body, timestamp, signature, signing_secret):
        return Response(content="Invalid signature", status_code=401)

    form = await request.form()
    command_text = form.get("text", "")
    response_url = form.get("response_url", "")

    # Spawn background task
    do_add_feed.spawn(response_url, command_text)

    # Immediate acknowledgment (empty 200 = Slack shows nothing)
    return Response(content="", status_code=200)


@app.function(secrets=[secrets], min_containers=1)
@modal.fastapi_endpoint(method="POST")
async def remove_feed(request: Request) -> Response:
    """Handle /watcher-remove-feed slash command."""
    import os

    signing_secret = os.environ["SLACK_SIGNING_SECRET"]

    body = await request.body()
    timestamp = request.headers.get("x-slack-request-timestamp", "")
    signature = request.headers.get("x-slack-signature", "")

    if not verify_slack_signature(body, timestamp, signature, signing_secret):
        return Response(content="Invalid signature", status_code=401)

    form = await request.form()
    feed_url = form.get("text", "").strip()
    response_url = form.get("response_url", "")

    # Spawn background task
    do_remove_feed.spawn(response_url, feed_url)

    return Response(content="", status_code=200)


@app.function(secrets=[secrets], min_containers=1)
@modal.fastapi_endpoint(method="POST")
async def pause(request: Request) -> Response:
    """Handle /watcher-pause slash command."""
    import os

    signing_secret = os.environ["SLACK_SIGNING_SECRET"]

    body = await request.body()
    timestamp = request.headers.get("x-slack-request-timestamp", "")
    signature = request.headers.get("x-slack-signature", "")

    if not verify_slack_signature(body, timestamp, signature, signing_secret):
        return Response(content="Invalid signature", status_code=401)

    form = await request.form()
    user_name = form.get("user_name", "unknown")
    response_url = form.get("response_url", "")

    # Spawn background task
    do_pause.spawn(response_url, user_name)

    return Response(content="", status_code=200)


@app.function(secrets=[secrets], min_containers=1)
@modal.fastapi_endpoint(method="POST")
async def unpause(request: Request) -> Response:
    """Handle /watcher-unpause slash command."""
    import os

    signing_secret = os.environ["SLACK_SIGNING_SECRET"]

    body = await request.body()
    timestamp = request.headers.get("x-slack-request-timestamp", "")
    signature = request.headers.get("x-slack-signature", "")

    if not verify_slack_signature(body, timestamp, signature, signing_secret):
        return Response(content="Invalid signature", status_code=401)

    form = await request.form()
    user_name = form.get("user_name", "unknown")
    response_url = form.get("response_url", "")

    # Spawn background task
    do_unpause.spawn(response_url, user_name)

    return Response(content="", status_code=200)

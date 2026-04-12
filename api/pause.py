"""
Vercel serverless function to pause the Watcher digest via Slack slash command.

Handles /watcher-pause slash command:
- Verifies Slack request signature
- Updates state.json in GitHub repo to set paused=true
- Returns confirmation message to Slack
"""

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

from _utils import (
    get_file_from_github,
    send_slack_response,
    update_file_on_github,
    verify_slack_signature,
)


# Default state when state.json doesn't exist
DEFAULT_STATE = {
    "paused": False,
    "paused_at": None,
    "paused_by": None,
}


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
                send_slack_response(
                    self, 401, "ephemeral", ":x: Invalid signature"
                )
                return

            # Parse form data to get user info
            form_data = parse_qs(body.decode("utf-8"))
            user_name = form_data.get("user_name", ["unknown"])[0]

            # Get current state from GitHub
            state, sha = get_file_from_github("state.json")

            if state is None:
                state = DEFAULT_STATE.copy()

            # Check if already paused
            if state.get("paused", False):
                paused_by = state.get("paused_by", "someone")
                paused_at = state.get("paused_at", "unknown time")
                send_slack_response(
                    self,
                    200,
                    "ephemeral",
                    f":pause_button: Watcher is already paused (by {paused_by} at {paused_at})"
                )
                return

            # Update state to paused
            state["paused"] = True
            state["paused_at"] = datetime.now(timezone.utc).isoformat()
            state["paused_by"] = user_name

            # Save to GitHub
            update_file_on_github(
                "state.json",
                state,
                sha,
                f"Pause watcher (by {user_name})"
            )

            send_slack_response(
                self,
                200,
                "in_channel",
                f":pause_button: Watcher paused by @{user_name}. Use `/watcher-unpause` to resume."
            )

        except Exception as e:
            send_slack_response(
                self,
                200,
                "ephemeral",
                f":x: Something went wrong: {str(e)}"
            )

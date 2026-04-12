"""
Vercel serverless function to unpause the Watcher digest via Slack slash command.

Handles /watcher-unpause slash command:
- Verifies Slack request signature
- Updates state.json in GitHub repo to set paused=false
- Returns confirmation message to Slack
"""

import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

from _utils import (
    get_file_from_github,
    send_slack_response,
    update_file_on_github,
    verify_slack_signature,
)


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

            # If no state file exists or not paused, nothing to do
            if state is None or not state.get("paused", False):
                send_slack_response(
                    self,
                    200,
                    "ephemeral",
                    ":arrow_forward: Watcher is already running!"
                )
                return

            # Update state to unpaused
            state["paused"] = False
            state["paused_at"] = None
            state["paused_by"] = None

            # Save to GitHub
            update_file_on_github(
                "state.json",
                state,
                sha,
                f"Unpause watcher (by {user_name})"
            )

            send_slack_response(
                self,
                200,
                "in_channel",
                f":arrow_forward: Watcher resumed by @{user_name}. Daily digests will continue."
            )

        except Exception as e:
            send_slack_response(
                self,
                200,
                "ephemeral",
                f":x: Something went wrong: {str(e)}"
            )

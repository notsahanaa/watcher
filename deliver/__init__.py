"""Deliver module - sends digest via email and Slack."""

from .slack import deliver_to_slack, format_digest_for_slack

__all__ = ["deliver_to_slack", "format_digest_for_slack"]

"""Unit tests for the Discord alert helper (step 12).

No real Discord server needed: these check the two decision points
(nothing configured -> log, not crash; something configured -> POST the
right payload to the right URL) by faking requests.post, the TP1 way --
hand-written inputs, a known expected call.
"""
from unittest.mock import patch

from flows import alerts


def test_no_webhook_configured_does_not_call_requests(monkeypatch):
    monkeypatch.setattr(alerts, "DISCORD_WEBHOOK_URL", "")
    with patch("flows.alerts.requests.post") as mock_post:
        alerts.send_discord_alert("test message")
    mock_post.assert_not_called()


def test_webhook_configured_posts_the_message(monkeypatch):
    monkeypatch.setattr(alerts, "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/fake")
    with patch("flows.alerts.requests.post") as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        alerts.send_discord_alert("test message")
    mock_post.assert_called_once_with(
        "https://discord.com/api/webhooks/fake",
        json={"content": "test message"},
        timeout=10,
    )

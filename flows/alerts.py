"""A Discord webhook alert, and a Prefect on_failure hook that sends it.

Plain requests.post to the webhook URL Discord gives you when you add an
"Incoming Webhook" integration to a channel -- no extra library needed,
same philosophy as the rest of the project: a documented HTTP call, not a
wrapper that hides what's actually being sent.

DISCORD_WEBHOOK_URL is read from the environment, not hard-coded (never a
secret in the repo -- see .env.example). If it isn't set, alerts are
logged instead of sent: a flow should never fail *harder* just because
notifications aren't configured yet, and this also means the hook is safe
to leave attached while running flows locally with no Discord server at
all.
"""
import logging
import os

import requests
from prefect.exceptions import MissingContextError
from prefect.logging import get_run_logger

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")


def _logger():
    """get_run_logger() only works inside a flow/task run -- fall back to a
    plain logger so this module stays testable (tests/test_alerts.py) and
    usable on its own (e.g. `python -m flows.alerts` for a manual smoke
    test) without needing a live Prefect run to call it from."""
    try:
        return get_run_logger()
    except MissingContextError:
        return logging.getLogger(__name__)


def send_discord_alert(message: str) -> None:
    """POST a message to the configured Discord webhook, or log it if none is set."""
    logger = _logger()
    if not DISCORD_WEBHOOK_URL:
        logger.warning("DISCORD_WEBHOOK_URL not set; alert not sent: %s", message)
        return
    response = requests.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=10)
    response.raise_for_status()


def discord_failure_hook(flow, flow_run, state) -> None:
    """Prefect on_failure hook: flow, flow_run, state are positional by
    convention (see prefect.flows.FlowStateHook) -- Prefect passes them by
    name if the hook's parameters are named flow/flow_run/state, which is
    why these names matter, not just their order."""
    send_discord_alert(
        f":rotating_light: Flow **{flow.name}** run `{flow_run.name}` failed. "
        f"State: {state.name}. Check the Prefect UI for logs."
    )

import sys

import requests

from consoleme.config import config
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.models import ExtendedRequestModel

log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()


async def send_slack_notification_new_request(extended_request: ExtendedRequestModel):
    """
    Sends a notification using specified webhook URL about a new request created
    """
    if not config.get("slack.notifications_enabled", False):
        return

    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    requester = extended_request.requester_email
    arn = extended_request.principal.principal_arn
    stats.count(function, tags={"user": requester, "arn": arn})

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": requester,
        "arn": arn,
        "message": "Incoming request for slack notification",
        "request": extended_request.dict(),
    }
    log.debug(log_data)
    slack_webhook_url = config.get("slack.webhook_url")
    if not slack_webhook_url:
        log_data["message"] = "Missing webhook URL for slack notification"
        # TODO: warn or error or some other level?
        log.warn(log_data)
        return
    payload = {"text": "Hello, world."}
    resp = requests.post(slack_webhook_url, json=payload)
    if resp.status_code != 200:
        log_data["message"] = "Error occurred sending slack notification"
        log_data["error"] = f"{resp.status_code} : {resp.text}"
        # TODO: warn or error or some other level?
        log.warn(log_data)
    else:
        log_data["message"] = "Slack notification sent"
        log.debug(log_data)

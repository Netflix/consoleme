import sys
import uuid

import tornado.escape
import ujson as json
from tornado.httpclient import AsyncHTTPClient, HTTPClientError, HTTPRequest
from tornado.httputil import HTTPHeaders

from consoleme.config import config
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.policies import get_policy_request_uri_v2
from consoleme.models import ExtendedRequestModel

log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()


def slack_preflight_check(func):
    async def shortcircuit():
        return None

    def wrapper(*args, **kwargs):
        if not config.get("slack.notifications_enabled", False):
            return shortcircuit()
        return func(*args, **kwargs)

    return wrapper


@slack_preflight_check
async def send_slack_notification_new_policy_request(
    extended_request: ExtendedRequestModel, admin_approved, approval_probe_approved
):
    """
    Sends a notification using specified webhook URL about a new request created
    """

    if admin_approved and config.get("slack.ignore_auto_admin_policies", False):
        # Don't send slack notifications for policies that were auto approved due to admin status
        return None

    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    requester = extended_request.requester_email
    arn = extended_request.principal.principal_arn
    stats.count(function, tags={"user": requester, "arn": arn})

    payload_id = uuid.uuid4()

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": requester,
        "arn": arn,
        "message": "Incoming request for slack notification",
        "request": extended_request.dict(),
        "admin_approved": admin_approved,
        "approval_probe_approved": approval_probe_approved,
        "payload_id": payload_id,
    }
    log.debug(log_data)

    payload = await _build_policy_payload(
        extended_request, requester, arn, admin_approved, approval_probe_approved
    )

    return await send_slack_notification(payload, payload_id)


@slack_preflight_check
async def send_slack_notification(payload, payload_id):
    """
    Sends a notification using specified webhook URL about a new request created
    """

    slack_webhook_url = config.get("slack.webhook_url")
    if not slack_webhook_url:
        log.error(
            f"Missing webhook URL for slack notification. Not sending payload: {payload_id}"
        )
        return

    http_headers = HTTPHeaders({"Content-Type": "application/json"})
    http_req = HTTPRequest(
        url=slack_webhook_url,
        method="POST",
        headers=http_headers,
        body=json.dumps(payload),
    )

    http_client = AsyncHTTPClient(force_instance=True)
    try:
        await http_client.fetch(request=http_req)
        log.debug(f"Slack notifications sent for payload: {payload_id}")
    except (ConnectionError, HTTPClientError) as e:
        log.error(
            f"Slack notifications could not be sent for payload: {payload_id} due to {str(e)}"
        )


async def _build_policy_payload(
    extended_request: ExtendedRequestModel,
    requester: str,
    arn: str,
    admin_approved: bool,
    approval_probe_approved: bool,
):
    request_uri = await get_policy_request_uri_v2(extended_request)
    pre_text = "A new request has been created"
    if admin_approved:
        pre_text += " and auto-approved by admin"
    elif approval_probe_approved:
        pre_text += " and auto-approved by auto-approval probe"

    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*<{request_uri}|ConsoleMe Policy Change Request>*",
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*User* \n {requester}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Resource* \n {arn}"},
            },
            {
                "type": "section",
                "fields": [
                    {"text": "*Justification*", "type": "mrkdwn"},
                    {"type": "plain_text", "text": "\n"},
                    {
                        "type": "plain_text",
                        "text": f"{tornado.escape.xhtml_escape(extended_request.justification)}",
                    },
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{pre_text}. Click *<{request_uri}|here>* to view it.",
                },
            },
        ]
    }
    return payload

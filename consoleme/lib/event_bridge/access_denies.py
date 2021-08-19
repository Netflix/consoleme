import re
import sys
import time
from datetime import datetime
from typing import Any, Dict

import sentry_sdk
import ujson as json
from asgiref.sync import sync_to_async
from cloudaux.aws.sts import boto3_cached_conn

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    DataNotRetrievable,
    MissingConfigurationValue,
)
from consoleme.lib.aws import (
    resource_arn_known_in_aws_config,
    simulate_iam_principal_action,
)
from consoleme.lib.dynamo import UserDynamoHandler
from consoleme.lib.plugins import get_plugin_by_name

aws = get_plugin_by_name(config.get("plugins.aws", "default_aws"))()
log = config.get_logger()


async def get_resource_from_cloudtrail_deny(ct_event):
    """
    Naive attempt to determine resource from Access Deny CloudTrail event. If we can't parse it from the
    Cloudtrail message, we return `*`.
    """
    resource = "*"
    error_message = ct_event.get("error_message", "")
    if not error_message:
        return resource
    if "on resource: arn:aws" in ct_event.get("error_message", ""):
        resource_re = re.match(
            r"^.* on resource: (arn:aws:.*?$)", ct_event["error_message"]
        )
        if resource_re and len(resource_re.groups()) == 1:
            resource = resource_re.groups()[0]
    return resource


async def generate_policy_from_cloudtrail_deny(ct_event):
    """
    Naive generation of policy from a cloudtrail deny event

    TODOS:
        * Check if resource can already perform action. If so. Check if resource policy permits the action
        * For an action with a resource, check if that resource exists (Assume role to an IAM role, for example)
        * Check if being denied for some other reason than policy allowance. IE SCP, permission boundary, etc.
    """
    if ct_event["error_code"] not in [
        "UnauthorizedOperation",
        "AccessDenied",
    ]:
        return None

    policy = {
        "Statement": [
            {
                "Action": [ct_event["event_call"]],
                "Effect": "Allow",
                "Resource": [ct_event["resource"]],
            }
        ],
        "Version": "2012-10-17",
    }
    return policy


async def detect_cloudtrail_denies_and_update_cache() -> Dict[str, Any]:
    log_data = {"function": f"{__name__}.{sys._getframe().f_code.co_name}"}
    dynamo = UserDynamoHandler()
    queue_arn = config.get(
        "event_bridge.detect_cloudtrail_denies_and_update_cache.queue_arn", ""
    ).format(region=config.region)
    if not queue_arn:
        raise MissingConfigurationValue(
            "Unable to find required configuration value: "
            "`event_bridge.detect_cloudtrail_denies_and_update_cache.queue_arn`"
        )
    queue_name = queue_arn.split(":")[-1]
    queue_account_number = queue_arn.split(":")[4]
    queue_region = queue_arn.split(":")[3]
    # Optionally assume a role before receiving messages from the queue
    queue_assume_role = config.get(
        "event_bridge.detect_cloudtrail_denies_and_update_cache.assume_role"
    )

    sqs_client = await sync_to_async(boto3_cached_conn)(
        "sqs",
        service_type="client",
        region=queue_region,
        retry_max_attempts=2,
        account_number=queue_account_number,
        assume_role=queue_assume_role,
    )

    queue_url_res = await sync_to_async(sqs_client.get_queue_url)(QueueName=queue_name)
    queue_url = queue_url_res.get("QueueUrl")
    if not queue_url:
        raise DataNotRetrievable(f"Unable to retrieve Queue URL for {queue_arn}")
    messages_awaitable = await sync_to_async(sqs_client.receive_message)(
        QueueUrl=queue_url, MaxNumberOfMessages=10
    )
    messages = messages_awaitable.get("Messages", [])
    num_events = 0
    while messages:
        ct_events = []
        processed_messages = []
        for message in messages:
            try:
                message_body = json.loads(message["Body"])
                if "Message" in message_body:
                    decoded_message = json.loads(message_body["Message"])["detail"]
                else:
                    decoded_message = message_body["detail"]
                event_name = decoded_message.get("eventName")
                event_source = decoded_message.get("eventSource")
                for event_source_substitution in config.get(
                    "event_bridge.detect_cloudtrail_denies_and_update_cache.event_bridge_substitutions",
                    [".amazonaws.com"],
                ):
                    event_source = event_source.replace(event_source_substitution, "")
                event_time = decoded_message.get("eventTime")
                utc_time = datetime.strptime(event_time, "%Y-%m-%dT%H:%M:%SZ")
                epoch_event_time = int(
                    (utc_time - datetime(1970, 1, 1)).total_seconds() * 1000
                )
                # Skip entries older than a day
                if int(time.time()) * 1000 - 86400 > epoch_event_time:
                    continue
                try:
                    session_name = decoded_message["userIdentity"]["arn"].split("/")[-1]
                except (
                    IndexError,
                    KeyError,
                ):  # If IAM user, there won't be a session name
                    session_name = ""
                try:
                    principal_arn = decoded_message["userIdentity"]["sessionContext"][
                        "sessionIssuer"
                    ]["arn"]
                except KeyError:  # Skip events without a parsable ARN
                    continue

                principal_details = {}
                principal_type = principal_arn.split(":")[-1].split("/")[0]
                account_id = principal_arn.split(":")[4]
                # TODO: If principal doesn't exist after the first query, we don't want to keep slamming AWS SDKs
                # trying to find principal for subsequent queries
                if principal_type == "role":
                    principal_details = await aws.fetch_iam_role(
                        account_id, principal_arn
                    )
                elif principal_type == "user":
                    principal_details = await aws.fetch_iam_user(
                        account_id, principal_arn
                    )
                owner = principal_details.get("owner")

                # TODO: Generate CT events by user / owning google group to notify them about problems with their roles
                # TODO: Find out what the problem is - Role policy doesn't allow it, SCP, PB, inline policy, or resource policy
                # Need a quick way like the team role stuff to evaluate policies and make that determination
                # If access is because a resource doesn't exist,  whether to notify. If a lot of similar alerts, consider not doing
                # it and recommend the correct fix

                event_call = f"{event_source}:{event_name}"
                ct_event = dict(
                    error_code=decoded_message.get("errorCode"),
                    error_message=decoded_message.get("errorMessage"),
                    arn=principal_arn,
                    principal_owner=owner,
                    session_name=session_name,
                    request_id=decoded_message["requestID"],
                    source_ip=decoded_message["sourceIPAddress"],
                    event_call=event_call,
                    epoch_event_time=epoch_event_time,
                    ttl=(epoch_event_time + 86400000) / 1000,
                )
                ct_event["resource"] = await get_resource_from_cloudtrail_deny(ct_event)
                ct_event["resource_known"] = await resource_arn_known_in_aws_config(
                    ct_event["resource"]
                )

                if ct_event["resource_known"]:
                    ct_event[
                        "iam_simulation_response"
                    ] = await simulate_iam_principal_action(
                        principal_arn,
                        ct_event["event_call"],
                        ct_event["resource"],
                        ct_event["source_ip"],
                    )
                generated_policy = await generate_policy_from_cloudtrail_deny(ct_event)
                if generated_policy:
                    ct_event["generated_policy"] = generated_policy
                ct_events.append(ct_event)
                num_events += 1
            except Exception as e:
                log.error({**log_data, "error": str(e)}, exc_info=True)
                sentry_sdk.capture_exception()
            processed_messages.append(
                {
                    "Id": message["MessageId"],
                    "ReceiptHandle": message["ReceiptHandle"],
                }
            )
        if processed_messages:
            await sync_to_async(sqs_client.delete_message_batch)(
                QueueUrl=queue_url, Entries=processed_messages
            )
        await sync_to_async(dynamo.batch_write_cloudtrail_events)(ct_events)
        messages_awaitable = await sync_to_async(sqs_client.receive_message)(
            QueueUrl=queue_url, MaxNumberOfMessages=10
        )
        messages = messages_awaitable.get("Messages", [])
    log_data["message"] = "Successfully cached Cloudtrail Access Denies"
    log_data["num_events"] = num_events
    log.debug(log_data)

    return log_data

import re
import sys
from datetime import datetime

import sentry_sdk
import ujson as json
from asgiref.sync import sync_to_async
from cloudaux.aws.sts import boto3_cached_conn

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    DataNotRetrievable,
    MissingConfigurationValue,
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
    if "on resource: arn:aws" in ct_event["error_message"]:
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


async def detect_cloudtrail_denies_and_update_cache():
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
    ct_events = []
    messages_awaitable = await sync_to_async(sqs_client.receive_message)(
        QueueUrl=queue_url, MaxNumberOfMessages=10
    )
    messages = messages_awaitable.get("Messages", [])
    while messages:
        processed_messages = []
        for message in messages:
            try:
                message_body = json.loads(message["Body"])
                decoded_message = json.loads(message_body["Message"])["detail"]
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
                try:
                    session_name = decoded_message["userIdentity"]["arn"].split("/")[-1]
                except (
                    IndexError,
                    KeyError,
                ):  # If IAM user, there won't be a session name
                    session_name = ""
                try:
                    role_arn = decoded_message["userIdentity"]["sessionContext"][
                        "sessionIssuer"
                    ]["arn"]
                except KeyError:  # Skip events without a parsable ARN
                    continue

                ct_event = dict(
                    error_code=decoded_message.get("errorCode"),
                    error_message=decoded_message.get("errorMessage"),
                    arn=role_arn,
                    session_name=session_name,
                    request_id=decoded_message["requestID"],
                    event_call=f"{event_source}:{event_name}",
                    epoch_event_time=epoch_event_time,
                    ttl=(epoch_event_time + 86400000) / 1000,
                )
                ct_event["resource"] = await get_resource_from_cloudtrail_deny(ct_event)
                generated_policy = await generate_policy_from_cloudtrail_deny(ct_event)
                if generated_policy:
                    ct_event["generated_policy"] = generated_policy
                ct_events.append(ct_event)
            except Exception as e:
                log.error({**log_data, "error": str(e)}, exc_info=True)
                sentry_sdk.capture_exception()
            processed_messages.append(
                {
                    "Id": message["MessageId"],
                    "ReceiptHandle": message["ReceiptHandle"],
                }
            )
        await sync_to_async(sqs_client.delete_message_batch)(
            QueueUrl=queue_url, Entries=processed_messages
        )
        await sync_to_async(dynamo.batch_write_cloudtrail_events)(ct_events)
        messages_awaitable = await sync_to_async(sqs_client.receive_message)(
            QueueUrl=queue_url, MaxNumberOfMessages=10
        )
        messages = messages_awaitable.get("Messages", [])
    log.debug(
        {
            **log_data,
            "num_events": len(ct_events),
            "message": "Successfully cached Cloudtrail Access Denies",
        }
    )

    return ct_events

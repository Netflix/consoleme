import sys

import sentry_sdk
import ujson as json
from cloudaux.aws.sts import boto3_cached_conn

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    DataNotRetrievable,
    MissingConfigurationValue,
)
from consoleme.lib.plugins import get_plugin_by_name

aws = get_plugin_by_name(config.get("plugins.aws", "default_aws"))()
log = config.get_logger()


def detect_role_changes_and_update_cache(celery_app):
    """
    This function detects role changes through event bridge rules, and forces a refresh of the roles.
    """
    log_data = {"function": f"{__name__}.{sys._getframe().f_code.co_name}"}
    queue_arn = config.get(
        "event_bridge.detect_role_changes_and_update_cache.queue_arn", ""
    ).format(region=config.region)

    if not queue_arn:
        raise MissingConfigurationValue(
            "Unable to find required configuration value: "
            "`event_bridge.detect_role_changes_and_update_cache.queue_arn`"
        )
    queue_name = queue_arn.split(":")[-1]
    queue_account_number = queue_arn.split(":")[4]
    queue_region = queue_arn.split(":")[3]
    # Optionally assume a role before receiving messages from the queue
    queue_assume_role = config.get(
        "event_bridge.detect_role_changes_and_update_cache.assume_role"
    )

    sqs_client = boto3_cached_conn(
        "sqs",
        service_type="client",
        region=queue_region,
        retry_max_attempts=2,
        account_number=queue_account_number,
        assume_role=queue_assume_role,
        client_kwargs=config.get("boto3.client_kwargs", {}),
    )

    queue_url_res = sqs_client.get_queue_url(QueueName=queue_name)
    queue_url = queue_url_res.get("QueueUrl")
    if not queue_url:
        raise DataNotRetrievable(f"Unable to retrieve Queue URL for {queue_arn}")
    roles_to_update = set()
    messages = sqs_client.receive_message(
        QueueUrl=queue_url, MaxNumberOfMessages=10
    ).get("Messages", [])

    while messages:
        processed_messages = []
        for message in messages:
            try:
                message_body = json.loads(message["Body"])
                try:
                    if "Message" in message_body:
                        decoded_message = json.loads(message_body["Message"])["detail"]
                    else:
                        decoded_message = message_body["detail"]
                except Exception as e:
                    log.error(
                        {
                            **log_data,
                            "message": "Unable to process Cloudtrail message",
                            "message_body": message_body,
                            "error": str(e),
                        }
                    )
                    sentry_sdk.capture_exception()
                    continue
                role_name = decoded_message["requestParameters"]["roleName"]
                role_account_id = decoded_message.get(
                    "account", decoded_message.get("recipientAccountId")
                )
                role_arn = f"arn:aws:iam::{role_account_id}:role/{role_name}"

                if role_arn not in roles_to_update:
                    celery_app.send_task(
                        "consoleme.celery_tasks.celery_tasks.refresh_iam_role",
                        args=[role_arn],
                    )
                roles_to_update.add(role_arn)
            except Exception as e:
                log.error(
                    {**log_data, "error": str(e), "raw_message": message}, exc_info=True
                )
                sentry_sdk.capture_exception()
            processed_messages.append(
                {
                    "Id": message["MessageId"],
                    "ReceiptHandle": message["ReceiptHandle"],
                }
            )
        sqs_client.delete_message_batch(QueueUrl=queue_url, Entries=processed_messages)
        messages = sqs_client.receive_message(
            QueueUrl=queue_url, MaxNumberOfMessages=10
        ).get("Messages", [])
    log.debug(
        {
            **log_data,
            "num_roles": len(roles_to_update),
            "message": "Triggered role cache update for roles that were created or changed",
        }
    )

    return roles_to_update

import os
import sys

import sentry_sdk
import ujson as json
from asgiref.sync import async_to_sync
from cloudaux.aws.sqs import delete_message_batch, get_queue_url, receive_message

from consoleme.config import config
from consoleme.lib.plugins import get_plugin_by_name

aws = get_plugin_by_name(config.get("plugins.aws", "default_aws"))()
log = config.get_logger()


async def detect_role_changes_and_update_cache():
    """
    This function detects role changes through event bridge rules, and forces a refresh of updated roles.
    """
    # MAKE CONFIGURABLE
    log_data = {"function": f"{__name__}.{sys._getframe().f_code.co_name}"}
    queue_arn = "arn:aws:sqs:us-east-1:313219654698:consoleme-cloudtrail-role-events-eventbridge-queue"
    queue_name = queue_arn.split(":")[-1]
    queue_account_number = queue_arn.split(":")[4]
    queue_region = queue_arn.split(":")[3]
    queue_assume_role = ""

    conn = dict(
        account_number=queue_account_number,
        assume_role=queue_assume_role,
        region=queue_region,
    )
    queue_url = get_queue_url(QueueName=queue_name, **conn)
    updated_roles = set()
    messages = receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10, **conn)
    while messages:
        processed_messages = []
        for message in messages:
            try:
                message_body = json.loads(message["Body"])
                role_name = message_body["detail"]["requestParameters"]["roleName"]
                role_account_id = message_body["account"]
                role_arn = f"arn:aws:iam::{role_account_id}:role/{role_name}"
                updated_roles.add(role_arn)

                # TODO: Trigger refresh of this role
                # TODO: Trigger credential authz mapping job
                # TODO: Modify credential authz mapping job to delete cache of users affected by recent changes
            except Exception as e:
                log.error({**log_data, "error": str(e)})
                sentry_sdk.capture_exception()
            processed_messages.append(
                {"Id": message["MessageId"], "ReceiptHandle": message["ReceiptHandle"]}
            )
        delete_message_batch(QueueUrl=queue_url, Entries=processed_messages, **conn)
    log.debug(
        {
            **log_data,
            "num_roles": len(updated_roles),
            "message": "Triggering role cache update for roles that were created or change",
        }
    )
    for role_arn in updated_roles:
        # TODO: Does this need to be parallelized?
        await aws.fetch_iam_role(role_arn.split(":")[4], role_arn, force_refresh=True)
    return updated_roles

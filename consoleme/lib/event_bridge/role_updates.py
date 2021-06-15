import asyncio
import os
import sys

import sentry_sdk
import ujson as json
from asgiref.sync import async_to_sync
from cloudaux.aws.sqs import delete_message_batch, get_queue_url, receive_message
from cloudaux.aws.sts import boto3_cached_conn

from consoleme.config import config
from consoleme.exceptions.exceptions import DataNotRetrievable
from consoleme.lib.asyncio import run_in_parallel
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.threading import GlobalThreadPool

aws = get_plugin_by_name(config.get("plugins.aws", "default_aws"))()
log = config.get_logger()
thread_pool = GlobalThreadPool()


async def detect_role_changes_and_update_cache():
    """
    This function detects role changes through event bridge rules, and forces a refresh of updated roles.
    """
    # TODO: MAKE CONFIGURABLE
    log_data = {"function": f"{__name__}.{sys._getframe().f_code.co_name}"}
    queue_arn = "arn:aws:sqs:us-east-1:441660064727:consoleme-cloudtrail-role-events"
    queue_name = queue_arn.split(":")[-1]
    queue_account_number = queue_arn.split(":")[4]
    queue_region = queue_arn.split(":")[3]
    queue_assume_role = ""
    # TODO: make SQS code generic
    sqs_client = boto3_cached_conn(
        "sqs",
        service_type="client",
        region=queue_region,
        retry_max_attempts=2,
        account_number=queue_account_number,
        assume_role=queue_assume_role,
    )

    queue_url_res = sqs_client.get_queue_url(QueueName=queue_name)
    queue_url = queue_url_res.get("QueueUrl")
    if not queue_url:
        raise DataNotRetrievable(f"Unable to retrieve Queue URL for {queue_arn}")
    roles_to_update = set()
    messages = sqs_client.receive_message(
        QueueUrl=queue_url, MaxNumberOfMessages=10
    ).get("Messages", [])
    tasks = []
    while messages:
        processed_messages = []
        for message in messages:
            try:
                # TODO: Speed this up
                message_body = json.loads(message["Body"])
                decoded_message = json.loads(message_body["Message"])
                role_name = decoded_message["detail"]["requestParameters"]["roleName"]
                role_account_id = decoded_message["account"]
                role_arn = f"arn:aws:iam::{role_account_id}:role/{role_name}"
                if role_arn not in roles_to_update:
                    tasks.append(
                        {
                            "fn": aws.fetch_iam_role,
                            "args": (role_arn.split(":")[4], role_arn),
                            "kwargs": {"force_refresh": True},
                        }
                    )
                roles_to_update.add(role_arn)
                # fut = await thread_pool.execute_in_background_thread_async(
                #     aws.fetch_iam_role,
                #     (role_arn.split(":")[4], role_arn),
                #     {
                #         "force_refresh": True
                #     }
                # )

                # await aws.fetch_iam_role(role_arn.split(":")[4], role_arn, force_refresh=True)
                processed_messages.append(
                    {
                        "Id": message["MessageId"],
                        "ReceiptHandle": message["ReceiptHandle"],
                    }
                )
            except Exception as e:
                log.error({**log_data, "error": str(e)}, exc_info=True)
                sentry_sdk.capture_exception()
        sqs_client.delete_message_batch(QueueUrl=queue_url, Entries=processed_messages)
        messages = sqs_client.receive_message(
            QueueUrl=queue_url, MaxNumberOfMessages=10
        ).get("Messages", [])
    res = await run_in_parallel(tasks, sync=False)
    print(res)
    log.debug(
        {
            **log_data,
            "num_roles": len(roles_to_update),
            "message": "Triggering role cache update for roles that were created or change",
        }
    )
    return roles_to_update

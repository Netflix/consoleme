from ctypes import Union
from datetime import datetime, timedelta

import json  # We use a separate SetEncoder here so we cannot use ujson
import sys
from asgiref.sync import async_to_sync
from cloudaux.aws.iam import get_account_authorization_details
from cloudaux.aws.sts import boto3_cached_conn
from consoleme.config import config
from consoleme.lib.cache import (
    store_json_results_in_redis_and_s3,
)
from consoleme.lib.dynamo import IAMRoleDynamoHandler
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.redis import RedisHandler
from typing import Dict

log = config.get_logger()
red = async_to_sync(RedisHandler().redis)()
stats = get_plugin_by_name(config.get("plugins.metrics"))()


def cache_sqs_queues_for_account(account_id: str) -> Dict[str, Union[str, int]]:
    all_queues: set = set()

    for region in config.get("celery.sync_regions"):
        client = boto3_cached_conn(
            "sqs",
            account_number=account_id,
            assume_role=config.get("policies.role_name", "ConsoleMe"),
            region=region,
            read_only=True,
        )

        paginator = client.get_paginator("list_queues")

        response_iterator = paginator.paginate(PaginationConfig={"PageSize": 1000})

        for res in response_iterator:
            for queue in res.get("QueueUrls", []):
                arn = f"arn:aws:sqs:{region}:{account_id}:{queue.split('/')[4]}"
                all_queues.add(arn)
    sqs_queue_key: str = config.get("redis.sqs_queues_key", "SQS_QUEUES")
    red.hset(sqs_queue_key, account_id, json.dumps(list(all_queues)))

    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "account_id": account_id,
        "number_sqs_queues": len(all_queues),
    }
    log.debug(log_data)
    stats.count(
        "cache_sqs_queues_for_account",
        tags={"account_id": account_id, "number_sqs_queues": len(all_queues)},
    )

    if config.region == config.get("celery.active_region") or config.get(
            "environment"
    ) in ["dev", "test"]:
        s3_bucket = config.get("account_resource_cache.s3.bucket")
        s3_key = config.get("account_resource_cache.s3.file", "").format(
            resource_type="sqs_queues", account_id=account_id
        )
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_queues, s3_bucket=s3_bucket, s3_key=s3_key
        )
    return log_data


def cache_iam_for_account(account_id: str) -> bool:
    # Get the DynamoDB handler:
    dynamo = IAMRoleDynamoHandler()
    cache_key = config.get("aws.iamroles_redis_key", "IAM_ROLE_CACHE")

    # Only query IAM and put data in Dynamo if we're in the active region
    if config.region == config.get("celery.active_region") or config.get(
        "unit_testing.override_true"
    ):
        # Get the roles:
        iam_roles = get_account_authorization_details(
            account_number=account_id,
            assume_role=config.get("policies.role_name"),
            region=config.region,
            filter="Role",
        )

        async_to_sync(store_json_results_in_redis_and_s3)(
            iam_roles,
            s3_bucket=config.get("cache_roles_for_account.s3.bucket"),
            s3_key=config.get("cache_roles_for_account.s3.file", "").format(
                resource_type="iam_roles", account_id=account_id
            ),
        )

        ttl: int = int((datetime.utcnow() + timedelta(hours=36)).timestamp())
        # Save them:
        for role in iam_roles:
            role_entry = {
                "arn": role.get("Arn"),
                "name": role.get("RoleName"),
                "accountId": account_id,
                "ttl": ttl,
                "policy": dynamo.convert_role_to_json(role),
                "templated": red.hget(
                    config.get("templated_roles.redis_key", "TEMPLATED_ROLES_v2"),
                    role.get("Arn").lower(),
                ),
            }

            # DynamoDB:
            dynamo.sync_iam_role_for_account(role_entry)

            # Redis:
            _add_role_to_redis(cache_key, role_entry)

            # Run internal function on role. This can be used to inspect roles, add managed policies, or other actions
            aws().handle_detected_role(role)

    stats.count("cache_roles_for_account.success", tags={"account_id": account_id})
    return True
"""
This module controls defines celery tasks and their applicable schedules. The celery beat server and workers will start
when invoked. Please add internal-only celery tasks to the celery_tasks plugin.

When ran in development mode (CONFIG_LOCATION=<location of development.yaml configuration file. To run both the celery
beat scheduler and a worker simultaneously, and to have jobs kick off starting at the next minute, run the following
command: celery -A consoleme.celery_tasks.celery_tasks worker --loglevel=info -l DEBUG -B

"""
from __future__ import absolute_import

import json  # We use a separate SetEncoder here so we cannot use ujson
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Union

import celery
import sentry_sdk
import ujson
from asgiref.sync import async_to_sync
from billiard.exceptions import SoftTimeLimitExceeded
from botocore.exceptions import ClientError
from celery.app.task import Context
from celery.concurrency import asynpool
from celery.schedules import crontab
from celery.signals import (
    task_failure,
    task_prerun,
    task_received,
    task_rejected,
    task_retry,
    task_revoked,
    task_success,
    task_unknown,
)
from cloudaux import sts_conn
from cloudaux.aws.iam import get_all_managed_policies
from cloudaux.aws.s3 import list_buckets
from cloudaux.aws.sns import list_topics
from cloudaux.aws.sts import boto3_cached_conn
from retrying import retry
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.tornado import TornadoIntegration

from consoleme.config import config
from consoleme.lib.account_indexers import (
    cache_cloud_accounts,
    get_account_id_to_name_mapping,
)
from consoleme.lib.aws import (
    cache_all_scps,
    cache_org_structure,
    get_enabled_regions_for_account,
)
from consoleme.lib.aws_config import aws_config
from consoleme.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from consoleme.lib.cloud_credential_authorization_mapping import (
    generate_and_store_credential_authorization_mapping,
)
from consoleme.lib.dynamo import IAMRoleDynamoHandler, UserDynamoHandler
from consoleme.lib.git import store_iam_resources_in_git
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.policies import get_aws_config_history_url_for_resource
from consoleme.lib.redis import RedisHandler
from consoleme.lib.requests import cache_all_policy_requests
from consoleme.lib.self_service.typeahead import cache_self_service_typeahead
from consoleme.lib.templated_resources import cache_resource_templates
from consoleme.lib.timeout import Timeout

asynpool.PROC_ALIVE_TIMEOUT = config.get("celery.asynpool_proc_alive_timeout", 60.0)
default_retry_kwargs = {
    "autoretry_for": (Exception,),
    "retry_backoff": True,
    "retry_kwargs": {"max_retries": config.get("celery.default_max_retries", 5)},
}


class Celery(celery.Celery):
    def on_configure(self) -> None:
        sentry_dsn = config.get("sentry.dsn")
        if sentry_dsn:
            sentry_sdk.init(
                sentry_dsn,
                integrations=[
                    TornadoIntegration(),
                    CeleryIntegration(),
                    AioHttpIntegration(),
                    RedisIntegration(),
                ],
            )


app = Celery(
    "tasks",
    broker=config.get(f"celery.broker.{config.region}", "redis://127.0.0.1:6379/1"),
    backend=config.get(f"celery.backend.{config.region}", "redis://127.0.0.1:6379/2"),
)

app.conf.result_expires = config.get("celery.result_expires", 60)
app.conf.worker_prefetch_multiplier = config.get("celery.worker_prefetch_multiplier", 4)
app.conf.task_acks_late = config.get("celery.task_acks_late", True)

if config.get("celery.purge"):
    # Useful to clear celery queue in development
    with Timeout(seconds=5, error_message="Timeout: Are you sure Redis is running?"):
        app.control.purge()

log = config.get_logger()
red = RedisHandler().redis_sync()
aws = get_plugin_by_name(config.get("plugins.aws", "default_aws"))
auth = get_plugin_by_name(config.get("plugins.auth", "default_auth"))()
group_mapping = get_plugin_by_name(
    config.get("plugins.group_mapping", "default_group_mapping")
)()
internal_celery_tasks = get_plugin_by_name(
    config.get("plugins.internal_celery_tasks", "default_celery_tasks")
)
stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
internal_policies = get_plugin_by_name(
    config.get("plugins.internal_policies", "default_policies")
)()
REDIS_IAM_COUNT = 1000


@app.task(soft_time_limit=20)
def report_celery_last_success_metrics() -> bool:
    """
    For each celery task, this will determine the number of seconds since it has last been successful.

    Celery tasks should be emitting redis stats with a deterministic key (In our case, `f"{task}.last_success"`.
    report_celery_last_success_metrics should be ran periodically to emit metrics on when a task was last successful.
    We can then alert when tasks are not ran when intended. We should also alert when no metrics are emitted
    from this function.
    """
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {"function": function}
    current_time = int(time.time())
    global schedule
    for _, t in schedule.items():
        task = t.get("task")
        last_success = int(red.get(f"{task}.last_success") or 0)
        if last_success == 0:
            log_data["message"] = "Last Success Value is 0"
            log_data["task_last_success_key"] = f"{task}.last_success"
            log.error(log_data)
        stats.gauge(f"{task}.time_since_last_success", current_time - last_success)
        red.set(f"{task}.time_since_last_success", current_time - last_success)
    red.set(
        f"{function}.last_success", int(time.time())
    )  # Alert if this metric is not seen

    stats.count(f"{function}.success")
    stats.timer("worker.healthy")
    return True


def get_celery_request_tags(**kwargs):
    request = kwargs.get("request")
    sender_hostname = "unknown"
    sender = kwargs.get("sender")

    if sender:
        try:
            sender_hostname = sender.hostname
        except AttributeError:
            sender_hostname = vars(sender.request).get("origin", "unknown")
    if request and not isinstance(
        request, Context
    ):  # unlike others, task_revoked sends a Context for `request`
        task_name = request.name
        task_id = request.id
        receiver_hostname = request.hostname
    else:
        try:
            task_name = sender.name
        except AttributeError:
            task_name = kwargs.pop("name", "")
        try:
            task_id = sender.request.id
        except AttributeError:
            task_id = kwargs.pop("id", "")
        try:
            receiver_hostname = sender.request.hostname
        except AttributeError:
            receiver_hostname = ""

    tags = {
        "task_name": task_name,
        "task_id": task_id,
        "sender_hostname": sender_hostname,
        "receiver_hostname": receiver_hostname,
    }

    tags["expired"] = kwargs.get("expired", False)
    exception = kwargs.get("exception")
    if not exception:
        exception = kwargs.get("exc")
    if exception:
        tags["error"] = repr(exception)
        if isinstance(exception, SoftTimeLimitExceeded):
            tags["timed_out"] = True
    return tags


@task_prerun.connect
def refresh_dynamic_config_in_worker(**kwargs):
    tags = get_celery_request_tags(**kwargs)
    log_data = {"function": f"{__name__}.{sys._getframe().f_code.co_name}"}

    dynamic_config = red.get("DYNAMIC_CONFIG_CACHE")
    if not dynamic_config:
        log.error({**log_data, "error": "Unable to retrieve Dynamic Config from Redis"})
        return
    dynamic_config_j = json.loads(dynamic_config)
    if config.CONFIG.config.get("dynamic_config", {}) != dynamic_config_j:
        log.debug(
            {
                **log_data,
                **tags,
                "message": "Refreshing dynamic configuration on Celery Worker",
            }
        )
        config.CONFIG.config["dynamic_config"] = dynamic_config_j


@task_received.connect
def report_number_pending_tasks(**kwargs):
    """
    Report the number of pending tasks to our metrics broker every time a task is published. This metric can be used
    for autoscaling workers.
    https://docs.celeryproject.org/en/latest/userguide/signals.html#task-received

    :param sender:
    :param headers:
    :param body:
    :param kwargs:
    :return:
    """
    tags = get_celery_request_tags(**kwargs)
    tags.pop("task_id", None)
    stats.timer("celery.new_pending_task", tags=tags)


@task_success.connect
def report_successful_task(**kwargs):
    """
    Report a generic success metric as tasks to our metrics broker every time a task finished correctly.
    This metric can be used for autoscaling workers.
    https://docs.celeryproject.org/en/latest/userguide/signals.html#task-success

    :param sender:
    :param headers:
    :param body:
    :param kwargs:
    :return:
    """
    tags = get_celery_request_tags(**kwargs)
    red.set(f"{tags['task_name']}.last_success", int(time.time()))
    tags.pop("error", None)
    tags.pop("task_id", None)
    stats.timer("celery.successful_task", tags=tags)


@task_retry.connect
def report_task_retry(**kwargs):
    """
    Report a generic retry metric as tasks to our metrics broker every time a task is retroed.
    This metric can be used for alerting.
    https://docs.celeryproject.org/en/latest/userguide/signals.html#task-retry

    :param sender:
    :param headers:
    :param body:
    :param kwargs:
    :return:
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Celery Task Retry",
    }

    # Add traceback if exception info is in the kwargs
    einfo = kwargs.get("einfo")
    if einfo:
        log_data["traceback"] = einfo.traceback

    error_tags = get_celery_request_tags(**kwargs)

    log_data.update(error_tags)
    log.error(log_data)
    error_tags.pop("error", None)
    error_tags.pop("task_id", None)
    stats.timer("celery.retried_task", tags=error_tags)


@task_failure.connect
def report_failed_task(**kwargs):
    """
    Report a generic failure metric as tasks to our metrics broker every time a task fails. This is also called when
    a task has hit a SoftTimeLimit.

    The metric emited by this function can be used for alerting.
    https://docs.celeryproject.org/en/latest/userguide/signals.html#task-failure

    :param sender:
    :param headers:
    :param body:
    :param kwargs:
    :return:
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Celery Task Failure",
    }

    # Add traceback if exception info is in the kwargs
    einfo = kwargs.get("einfo")
    if einfo:
        log_data["traceback"] = einfo.traceback

    error_tags = get_celery_request_tags(**kwargs)

    log_data.update(error_tags)
    log.error(log_data)
    error_tags.pop("error", None)
    error_tags.pop("task_id", None)
    stats.timer("celery.failed_task", tags=error_tags)


@task_unknown.connect
def report_unknown_task(**kwargs):
    """
    Report a generic failure metric as tasks to our metrics broker every time a worker receives an unknown task.
    The metric emited by this function can be used for alerting.
    https://docs.celeryproject.org/en/latest/userguide/signals.html#task-unknown

    :param sender:
    :param headers:
    :param body:
    :param kwargs:
    :return:
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Celery Task Unknown",
    }

    error_tags = get_celery_request_tags(**kwargs)

    log_data.update(error_tags)
    log.error(log_data)
    error_tags.pop("error", None)
    error_tags.pop("task_id", None)
    stats.timer("celery.unknown_task", tags=error_tags)


@task_rejected.connect
def report_rejected_task(**kwargs):
    """
    Report a generic failure metric as tasks to our metrics broker every time a task is rejected.
    The metric emited by this function can be used for alerting.
    https://docs.celeryproject.org/en/latest/userguide/signals.html#task-rejected

    :param sender:
    :param headers:
    :param body:
    :param kwargs:
    :return:
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Celery Task Rejected",
    }

    error_tags = get_celery_request_tags(**kwargs)

    log_data.update(error_tags)
    log.error(log_data)
    error_tags.pop("error", None)
    error_tags.pop("task_id", None)
    stats.timer("celery.rejected_task", tags=error_tags)


@task_revoked.connect
def report_revoked_task(**kwargs):
    """
    Report a generic failure metric as tasks to our metrics broker every time a task is revoked.
    This metric can be used for alerting.
    https://docs.celeryproject.org/en/latest/userguide/signals.html#task-revoked

    :param sender:
    :param headers:
    :param body:
    :param kwargs:
    :return:
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Celery Task Revoked",
    }

    error_tags = get_celery_request_tags(**kwargs)

    log_data.update(error_tags)
    log.error(log_data)
    error_tags.pop("error", None)
    error_tags.pop("task_id", None)
    stats.timer("celery.revoked_task", tags=error_tags)


@retry(
    stop_max_attempt_number=4,
    wait_exponential_multiplier=1000,
    wait_exponential_max=1000,
)
def _add_role_to_redis(redis_key: str, role_entry: Dict) -> None:
    """
    This function will add IAM role data to redis so that policy details can be quickly retrieved by the policies
    endpoint.

    IAM role data is stored in the `redis_key` redis key by the role's ARN.

    Parameters
    ----------
    redis_key : str
        The redis key (hash)
    role_entry : Dict
        The role entry
        Example: {'name': 'nameOfRole', 'accountId': '123456789012', 'arn': 'arn:aws:iam::123456789012:role/nameOfRole',
        'templated': None, 'ttl': 1562510908, 'policy': '<json_formatted_policy>'}
    """
    try:
        red.hset(redis_key, role_entry["arn"], json.dumps(role_entry))
    except Exception as e:  # noqa
        stats.count(
            "cache_roles_for_account.error",
            tags={"redis_key": redis_key, "error": str(e), "role_entry": role_entry},
        )
        log_data = {
            "message": "Error syncing Account's IAM roles to Redis",
            "account_id": role_entry["account_id"],
            "arn": role_entry["arn"],
            "role_entry": role_entry,
        }
        log.error(log_data, exc_info=True)
        raise


@app.task(soft_time_limit=3600)
def cache_cloudtrail_errors_by_arn() -> Dict:
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data: Dict = {"function": function}
    cloudtrail_errors: Dict = internal_policies.error_count_by_arn()
    if not cloudtrail_errors:
        cloudtrail_errors = {}
    red.setex(
        config.get(
            "celery.cache_cloudtrail_errors_by_arn.redis_key",
            "CLOUDTRAIL_ERRORS_BY_ARN",
        ),
        86400,
        json.dumps(cloudtrail_errors),
    )
    log_data["number_of_roles_with_errors"]: len(cloudtrail_errors.keys())
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=1800)
def cache_policies_table_details() -> bool:
    iam_role_redis_key = config.get("aws.iamroles_redis_key", "IAM_ROLE_CACHE")
    all_iam_roles = red.hgetall(iam_role_redis_key)
    items = []
    accounts_d = async_to_sync(get_account_id_to_name_mapping)()

    cloudtrail_errors = {}
    cloudtrail_errors_j = red.get(
        config.get(
            "celery.cache_cloudtrail_errors_by_arn.redis_key",
            "CLOUDTRAIL_ERRORS_BY_ARN",
        )
    )

    if cloudtrail_errors_j:
        cloudtrail_errors = json.loads(cloudtrail_errors_j)

    s3_error_topic = config.get("redis.s3_errors", "S3_ERRORS")
    all_s3_errors = red.get(s3_error_topic)
    s3_errors = {}
    if all_s3_errors:
        s3_errors = json.loads(all_s3_errors)

    for arn, role_details_j in all_iam_roles.items():
        role_details = ujson.loads(role_details_j)
        error_count = cloudtrail_errors.get(arn, 0)
        s3_errors_for_arn = s3_errors.get(arn, [])
        for error in s3_errors_for_arn:
            error_count += int(error.get("count"))

        account_id = arn.split(":")[4]
        account_name = accounts_d.get(str(account_id), "Unknown")
        resource_id = role_details.get("resourceId")
        items.append(
            {
                "account_id": account_id,
                "account_name": account_name,
                "arn": arn,
                "technology": "iam",
                "templated": red.hget(
                    config.get("templated_roles.redis_key", "TEMPLATED_ROLES_v2"),
                    arn.lower(),
                ),
                "errors": error_count,
                "config_history_url": async_to_sync(
                    get_aws_config_history_url_for_resource
                )(account_id, resource_id, arn, "AWS::IAM::Role"),
            }
        )
    s3_bucket_key: str = config.get("redis.s3_bucket_key", "S3_BUCKETS")
    s3_accounts = red.hkeys(s3_bucket_key)
    if s3_accounts:
        for account in s3_accounts:
            account_name = accounts_d.get(str(account), "Unknown")
            buckets = json.loads(red.hget(s3_bucket_key, account))

            for bucket in buckets:
                bucket_arn = f"arn:aws:s3:::{bucket}"
                s3_errors_for_arn = s3_errors.get(bucket_arn, [])

                error_count = 0
                for error in s3_errors_for_arn:
                    error_count += int(error.get("count"))
                items.append(
                    {
                        "account_id": account,
                        "account_name": account_name,
                        "arn": f"arn:aws:s3:::{bucket}",
                        "technology": "s3",
                        "templated": None,
                        "errors": error_count,
                    }
                )

    sns_topic_key: str = config.get("redis.sns_topics_key", "SNS_TOPICS")
    sns_accounts = red.hkeys(sns_topic_key)
    if sns_accounts:
        for account in sns_accounts:
            account_name = accounts_d.get(str(account), "Unknown")
            topics = json.loads(red.hget(sns_topic_key, account))

            for topic in topics:
                error_count = 0
                items.append(
                    {
                        "account_id": account,
                        "account_name": account_name,
                        "arn": topic,
                        "technology": "sns",
                        "templated": None,
                        "errors": error_count,
                    }
                )

    sqs_queue_key: str = config.get("redis.sqs_queues_key", "SQS_QUEUES")
    sqs_accounts = red.hkeys(sqs_queue_key)
    if sqs_accounts:
        for account in sqs_accounts:
            account_name = accounts_d.get(str(account), "Unknown")
            queues = json.loads(red.hget(sqs_queue_key, account))

            for queue in queues:
                error_count = 0
                items.append(
                    {
                        "account_id": account,
                        "account_name": account_name,
                        "arn": queue,
                        "technology": "sqs",
                        "templated": None,
                        "errors": error_count,
                    }
                )

    resources_from_aws_config_redis_key: str = config.get(
        "aws_config_cache.redis_key", "AWSCONFIG_RESOURCE_CACHE"
    )
    resources_from_aws_config = red.hgetall(resources_from_aws_config_redis_key)
    if resources_from_aws_config:
        for arn, value in resources_from_aws_config.items():
            resource = json.loads(value)
            technology = resource["resourceType"]
            # Skip technologies that we retrieve directly
            if technology in [
                "AWS::IAM::Role",
                "AWS::SQS::Queue",
                "AWS::SNS::Topic",
                "AWS::S3::Bucket",
            ]:
                continue
            account_id = arn.split(":")[4]
            account_name = accounts_d.get(account_id, "Unknown")
            items.append(
                {
                    "account_id": account_id,
                    "account_name": account_name,
                    "arn": arn,
                    "technology": technology,
                    "templated": None,
                    "errors": 0,
                }
            )

    s3_bucket = None
    s3_key = None
    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev", "test"]:
        s3_bucket = config.get("cache_policies_table_details.s3.bucket")
        s3_key = config.get(
            "cache_policies_table_details.s3.file",
            "policies_table/cache_policies_table_details_v1.json.gz",
        )
    async_to_sync(store_json_results_in_redis_and_s3)(
        items,
        redis_key=config.get("policies.redis_policies_key", "ALL_POLICIES"),
        s3_bucket=s3_bucket,
        s3_key=s3_key,
    )
    stats.count(
        "cache_policies_table_details.success",
        tags={"num_roles": len(all_iam_roles.keys())},
    )
    return True


@app.task(soft_time_limit=2700, **default_retry_kwargs)
def cache_roles_for_account(account_id: str) -> bool:
    # Get the DynamoDB handler:
    dynamo = IAMRoleDynamoHandler()
    cache_key = config.get("aws.iamroles_redis_key", "IAM_ROLE_CACHE")
    # Only query IAM and put data in Dynamo if we're in the active region
    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev", "test"]:
        client = boto3_cached_conn(
            "iam",
            account_number=account_id,
            assume_role=config.get("policies.role_name"),
            region=config.region,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
        )
        paginator = client.get_paginator("get_account_authorization_details")
        response_iterator = paginator.paginate()
        all_iam_resources = {}
        for response in response_iterator:
            if not all_iam_resources:
                all_iam_resources = response
            else:
                all_iam_resources["UserDetailList"].extend(response["UserDetailList"])
                all_iam_resources["GroupDetailList"].extend(response["GroupDetailList"])
                all_iam_resources["RoleDetailList"].extend(response["RoleDetailList"])
                all_iam_resources["Policies"].extend(response["Policies"])
            for k in response.keys():
                if k not in [
                    "UserDetailList",
                    "GroupDetailList",
                    "RoleDetailList",
                    "Policies",
                    "ResponseMetadata",
                    "Marker",
                    "IsTruncated",
                ]:
                    # Fail hard if we find something unexpected
                    raise RuntimeError("Unexpected key {0} in response".format(k))

        # Store entire response in S3
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_iam_resources,
            s3_bucket=config.get("cache_iam_resources_for_account.s3.bucket"),
            s3_key=config.get(
                "cache_iam_resources_for_account.s3.file",
                "get_account_authorization_details/get_account_authorization_details_{account_id}_v1.json.gz",
            ).format(account_id=account_id),
        )

        iam_roles = all_iam_resources["RoleDetailList"]

        async_to_sync(store_json_results_in_redis_and_s3)(
            iam_roles,
            s3_bucket=config.get("cache_roles_for_account.s3.bucket"),
            s3_key=config.get(
                "cache_roles_for_account.s3.file",
                "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
            ).format(resource_type="iam_roles", account_id=account_id),
        )

        ttl: int = int((datetime.utcnow() + timedelta(hours=36)).timestamp())
        # Save them:
        for role in iam_roles:
            role_entry = {
                "arn": role.get("Arn"),
                "name": role.get("RoleName"),
                "resourceId": role.get("RoleId"),
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

        # Maybe store all resources in git
        if config.get("cache_iam_resources_for_account.store_in_git.enabled"):
            store_iam_resources_in_git(all_iam_resources, account_id)

    stats.count("cache_roles_for_account.success", tags={"account_id": account_id})
    return True


@app.task(soft_time_limit=3600)
def cache_roles_across_accounts() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"

    cache_key = config.get("aws.iamroles_redis_key", "IAM_ROLE_CACHE")

    log_data = {"function": function, "cache_key": cache_key}
    num_accounts = 0
    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev", "test"]:
        # First, get list of accounts
        accounts_d = async_to_sync(get_account_id_to_name_mapping)()
        # Second, call tasks to enumerate all the roles across all accounts
        for account_id in accounts_d.keys():
            if config.get("environment") in ["prod", "dev"]:
                cache_roles_for_account.delay(account_id)
                num_accounts += 1
            else:
                if account_id in config.get("celery.test_account_ids", []):
                    cache_roles_for_account.delay(account_id)
                    num_accounts += 1
    else:
        dynamo = IAMRoleDynamoHandler()
        # In non-active regions, we just want to sync DDB data to Redis
        roles = dynamo.fetch_all_roles()
        for role_entry in roles:
            _add_role_to_redis(cache_key, role_entry)

    # Delete roles in Redis cache with expired TTL
    all_roles = red.hgetall(cache_key)
    roles_to_delete_from_cache = []
    for arn, role_entry_j in all_roles.items():
        role_entry = json.loads(role_entry_j)
        if datetime.fromtimestamp(role_entry["ttl"]) < datetime.utcnow():
            roles_to_delete_from_cache.append(arn)
    if roles_to_delete_from_cache:
        red.hdel(cache_key, *roles_to_delete_from_cache)
        for arn in roles_to_delete_from_cache:
            all_roles.pop(arn, None)
    log_data["num_roles"] = len(all_roles)
    # Store full list of roles in a single place. This list will be ~30 minutes out of date.
    async_to_sync(store_json_results_in_redis_and_s3)(
        all_roles,
        s3_bucket=config.get(
            "cache_roles_across_accounts.all_roles_combined.s3.bucket"
        ),
        s3_key=config.get(
            "cache_roles_across_accounts.all_roles_combined.s3.file",
            "account_resource_cache/cache_all_roles_v1.json.gz",
        ),
    )

    stats.count(f"{function}.success")
    log_data["num_accounts"] = num_accounts
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_managed_policies_for_account(account_id: str) -> Dict[str, Union[str, int]]:
    managed_policies: List[Dict] = get_all_managed_policies(
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        region=config.region,
    )
    all_policies: List = []
    for policy in managed_policies:
        all_policies.append(policy.get("Arn"))

    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "account_id": account_id,
        "number_managed_policies": len(all_policies),
    }
    log.debug(log_data)
    stats.count(
        "cache_managed_policies_for_account",
        tags={"account_id": account_id, "num_managed_policies": len(all_policies)},
    )

    policy_key = config.get("redis.iam_managed_policies_key", "IAM_MANAGED_POLICIES")
    red.hset(policy_key, account_id, json.dumps(all_policies))

    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev", "test"]:
        s3_bucket = config.get("account_resource_cache.s3.bucket")
        s3_key = config.get(
            "account_resource_cache.s3.file",
            "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
        ).format(resource_type="managed_policies", account_id=account_id)
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_policies, s3_bucket=s3_bucket, s3_key=s3_key
        )
    return log_data


@app.task(soft_time_limit=120)
def cache_managed_policies_across_accounts() -> bool:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    # First, get list of accounts
    accounts_d = async_to_sync(get_account_id_to_name_mapping)()
    # Second, call tasks to enumerate all the roles across all accounts
    for account_id in accounts_d.keys():
        if config.get("environment") == "prod":
            cache_managed_policies_for_account.delay(account_id)
        else:
            if account_id in config.get("celery.test_account_ids", []):
                cache_managed_policies_for_account.delay(account_id)

    stats.count(f"{function}.success")
    return True


@app.task(soft_time_limit=120)
def cache_s3_buckets_across_accounts() -> bool:
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    # First, get list of accounts
    accounts_d: List = async_to_sync(get_account_id_to_name_mapping)()
    # Second, call tasks to enumerate all the roles across all accounts
    for account_id in accounts_d.keys():
        if config.get("environment") == "prod":
            cache_s3_buckets_for_account.delay(account_id)
        else:
            if account_id in config.get("celery.test_account_ids", []):
                cache_s3_buckets_for_account.delay(account_id)
    stats.count(f"{function}.success")
    return True


@app.task(soft_time_limit=120)
def cache_sqs_queues_across_accounts() -> bool:
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    # First, get list of accounts
    accounts_d: List = async_to_sync(get_account_id_to_name_mapping)()
    # Second, call tasks to enumerate all the roles across all accounts
    for account_id in accounts_d.keys():
        if config.get("environment") == "prod":
            cache_sqs_queues_for_account.delay(account_id)
        else:
            if account_id in config.get("celery.test_account_ids", []):
                cache_sqs_queues_for_account.delay(account_id)
    stats.count(f"{function}.success")
    return True


@app.task(soft_time_limit=120)
def cache_sns_topics_across_accounts() -> bool:
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    # First, get list of accounts
    accounts_d: List = async_to_sync(get_account_id_to_name_mapping)()
    for account_id in accounts_d.keys():
        if config.get("environment") == "prod":
            cache_sns_topics_for_account.delay(account_id)
        else:
            if account_id in config.get("celery.test_account_ids", []):
                cache_sns_topics_for_account.delay(account_id)
    stats.count(f"{function}.success")
    return True


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_sqs_queues_for_account(account_id: str) -> Dict[str, Union[str, int]]:
    all_queues: set = set()
    enabled_regions = async_to_sync(get_enabled_regions_for_account)(account_id)
    for region in enabled_regions:
        client = boto3_cached_conn(
            "sqs",
            account_number=account_id,
            assume_role=config.get("policies.role_name"),
            region=region,
            read_only=True,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
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

    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev", "test"]:
        s3_bucket = config.get("account_resource_cache.s3.bucket")
        s3_key = config.get(
            "account_resource_cache.s3.file",
            "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
        ).format(resource_type="sqs_queues", account_id=account_id)
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_queues, s3_bucket=s3_bucket, s3_key=s3_key
        )
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_sns_topics_for_account(account_id: str) -> Dict[str, Union[str, int]]:
    # Make sure it is regional
    all_topics: set = set()
    enabled_regions = async_to_sync(get_enabled_regions_for_account)(account_id)
    for region in enabled_regions:
        topics = list_topics(
            account_number=account_id,
            assume_role=config.get("policies.role_name"),
            region=region,
            read_only=True,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
        )
        for topic in topics:
            all_topics.add(topic["TopicArn"])
    sns_topic_key: str = config.get("redis.sns_topics_key", "SNS_TOPICS")
    red.hset(sns_topic_key, account_id, json.dumps(list(all_topics)))

    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "account_id": account_id,
        "number_sns_topics": len(all_topics),
    }
    log.debug(log_data)
    stats.count(
        "cache_sns_topics_for_account",
        tags={"account_id": account_id, "number_sns_topics": len(all_topics)},
    )

    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev", "test"]:
        s3_bucket = config.get("account_resource_cache.s3.bucket")
        s3_key = config.get(
            "account_resource_cache.s3.file",
            "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
        ).format(resource_type="sns_topics", account_id=account_id)
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_topics, s3_bucket=s3_bucket, s3_key=s3_key
        )
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_s3_buckets_for_account(account_id: str) -> Dict[str, Union[str, int]]:
    s3_buckets: List = list_buckets(
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        region=config.region,
        read_only=True,
    )
    buckets: List = []
    for bucket in s3_buckets["Buckets"]:
        buckets.append(bucket["Name"])
    s3_bucket_key: str = config.get("redis.s3_buckets_key", "S3_BUCKETS")
    red.hset(s3_bucket_key, account_id, json.dumps(buckets))

    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "account_id": account_id,
        "number_s3_buckets": len(buckets),
    }
    log.debug(log_data)
    stats.count(
        "cache_s3_buckets_for_account",
        tags={"account_id": account_id, "number_sns_topics": len(buckets)},
    )

    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev", "test"]:
        s3_bucket = config.get("account_resource_cache.s3.bucket")
        s3_key = config.get(
            "account_resource_cache.s3.file",
            "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
        ).format(resource_type="s3_buckets", account_id=account_id)
        async_to_sync(store_json_results_in_redis_and_s3)(
            buckets, s3_bucket=s3_bucket, s3_key=s3_key
        )
    return log_data


@retry(
    stop_max_attempt_number=4,
    wait_exponential_multiplier=1000,
    wait_exponential_max=1000,
)
def _scan_redis_iam_cache(
    cache_key: str, index: int, count: int
) -> Tuple[int, Dict[str, str]]:
    return red.hscan(cache_key, index, count=count)


@app.task(soft_time_limit=1800)
def clear_old_redis_iam_cache() -> bool:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    # Do not run if this is not in the active region:
    if config.region != config.get("celery.active_region", config.region):
        return False

    # Need to loop over all items in the set:
    cache_key: str = config.get("aws.iamroles_redis_key", "IAM_ROLE_CACHE")
    index: int = 0
    expire_ttl: int = int((datetime.utcnow() - timedelta(hours=6)).timestamp())
    roles_to_expire = []

    # We will loop over REDIS_IAM_COUNT items at a time:
    try:
        while True:
            results = _scan_redis_iam_cache(cache_key, index, REDIS_IAM_COUNT)
            index = results[0]

            # Verify if the role is too old:
            for arn, role in results[1].items():
                role = json.loads(role)

                if role["ttl"] <= expire_ttl:
                    roles_to_expire.append(arn)

            # We will be complete if the next index is 0:
            if not index:
                break

    except:  # noqa
        log_data = {
            "function": function,
            "message": "Error retrieving roles from Redis for cache cleanup.",
        }
        log.error(log_data, exc_info=True)
        raise

    # Delete all the roles that we need to delete:
    try:
        if roles_to_expire:
            red.hdel(cache_key, *roles_to_expire)
    except:  # noqa
        log_data = {
            "function": function,
            "message": "Error deleting roles from Redis for cache cleanup.",
        }
        log.error(log_data, exc_info=True)
        raise

    stats.count(f"{function}.success", tags={"expired_roles": len(roles_to_expire)})
    return True


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_resources_from_aws_config_for_account(account_id) -> dict:
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    s3_bucket = config.get("aws_config_cache.s3.bucket")
    s3_key = config.get(
        "aws_config_cache.s3.file", "aws_config_cache/cache_{account_id}_v1.json.gz"
    ).format(account_id=account_id)
    dynamo = UserDynamoHandler()
    # Only query in active region, otherwise get data from DDB
    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev", "test"]:
        results = aws_config.query(
            config.get(
                "cache_all_resources_from_aws_config.aws_config.all_resources_query",
                "select * where accountId = '{account_id}'",
            ).format(account_id=account_id),
            use_aggregator=False,
            account_id=account_id,
        )

        ttl: int = int((datetime.utcnow() + timedelta(hours=36)).timestamp())
        redis_result_set = {}
        for result in results:
            result["ttl"] = ttl
            if result.get("arn"):
                if redis_result_set.get(result["arn"]):
                    continue
                redis_result_set[result["arn"]] = json.dumps(result)
        if redis_result_set:
            async_to_sync(store_json_results_in_redis_and_s3)(
                redis_result_set,
                redis_key=config.get(
                    "aws_config_cache.redis_key", "AWSCONFIG_RESOURCE_CACHE"
                ),
                redis_data_type="hash",
                s3_bucket=s3_bucket,
                s3_key=s3_key,
            )

            dynamo.write_resource_cache_data(results)
    else:
        redis_result_set = async_to_sync(retrieve_json_data_from_redis_or_s3)(
            s3_bucket=s3_bucket, s3_key=s3_key
        )

        async_to_sync(store_json_results_in_redis_and_s3)(
            redis_result_set,
            redis_key=config.get(
                "aws_config_cache.redis_key", "AWSCONFIG_RESOURCE_CACHE"
            ),
            redis_data_type="hash",
        )
    log_data = {
        "function": function,
        "account_id": account_id,
        "number_resources_synced": len(redis_result_set),
    }
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=1800)
def cache_resources_from_aws_config_across_accounts() -> bool:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    resource_redis_cache_key = config.get(
        "aws_config_cache.redis_key", "AWSCONFIG_RESOURCE_CACHE"
    )

    # First, get list of accounts
    accounts_d = async_to_sync(get_account_id_to_name_mapping)()
    # Second, call tasks to enumerate all the roles across all accounts
    for account_id in accounts_d.keys():
        if config.get("environment") in ["prod", "dev"]:
            cache_resources_from_aws_config_for_account.delay(account_id)
        else:
            if account_id in config.get("celery.test_account_ids", []):
                cache_resources_from_aws_config_for_account.delay(account_id)

    # Delete roles in Redis cache with expired TTL
    all_resources = red.hgetall(resource_redis_cache_key)
    if all_resources:
        expired_arns = []
        for arn, resource_entry_j in all_resources.items():
            resource_entry = ujson.loads(resource_entry_j)
            if datetime.fromtimestamp(resource_entry["ttl"]) < datetime.utcnow():
                expired_arns.append(arn)
        if expired_arns:
            red.hdel(resource_redis_cache_key, *expired_arns)

        # Cache all resource ARNs into a single file. Note: This runs synchronously with this task. This task triggers
        # resource collection on all accounts to happen asynchronously. That means when we store or delete data within
        # this task, we're always going to be caching the results from the previous task.
        if config.region == config.get(
            "celery.active_region", config.region
        ) or config.get("environment") in ["dev"]:
            # Refresh all resources after deletion of expired entries
            all_resources = red.hgetall(resource_redis_cache_key)
            s3_bucket = config.get("aws_config_cache_combined.s3.bucket")
            s3_key = config.get(
                "aws_config_cache_combined.s3.file",
                "aws_config_cache_combined/aws_config_resource_cache_combined_v1.json.gz",
            )
            async_to_sync(store_json_results_in_redis_and_s3)(
                all_resources, s3_bucket=s3_bucket, s3_key=s3_key
            )
    stats.count(f"{function}.success")
    return True


@app.task(soft_time_limit=1800)
def get_iam_role_limit() -> dict:
    """
    This function will gather the number of existing IAM Roles and IAM Role quota in all owned AWS accounts.
    """
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    num_accounts = 0
    num_roles = 0

    if not config.get("celery.get_iam_role_limit.enabled"):
        return {}

    success_message = "Not running - Inactive region"
    if config.region == config.get(
        "celery.active_region", config.region
    ) and config.get("environment") in ["prod", "dev"]:

        @sts_conn("iam")
        def _get_delivery_channels(**kwargs) -> list:
            """Gets the delivery channels in the account/region -- calls are wrapped with CloudAux"""
            return kwargs.pop("client").get_account_summary(**kwargs)

        success_message = "Task successfully completed"

        # First, get list of accounts
        accounts_d: Dict = async_to_sync(get_account_id_to_name_mapping)()
        num_accounts = len(accounts_d.keys())
        for account_id, account_name in accounts_d.items():
            try:
                iam_summary = _get_delivery_channels(
                    account_number=account_id,
                    assume_role=config.get("policies.role_name"),
                    region=config.region,
                )
                num_iam_roles = iam_summary["SummaryMap"]["Roles"]
                iam_role_quota = iam_summary["SummaryMap"]["RolesQuota"]
                iam_role_quota_ratio = num_iam_roles / iam_role_quota

                num_roles += num_iam_roles
                log_data = {
                    "function": function,
                    "message": "IAM role quota for account",
                    "num_iam_roles": num_iam_roles,
                    "iam_role_quota": iam_role_quota,
                    "iam_role_quota_ratio": iam_role_quota_ratio,
                    "account_id": account_id,
                    "account_name": account_name,
                }
                stats.gauge(
                    f"{function}.quota_ratio_gauge",
                    iam_role_quota_ratio,
                    tags={
                        "num_iam_roles": num_iam_roles,
                        "iam_role_quota": iam_role_quota,
                        "account_id": account_id,
                        "account_name": account_name,
                    },
                )
                log.debug(log_data)
            except ClientError as e:
                log_data = {
                    "function": function,
                    "message": "Error retrieving IAM quota",
                    "account_id": account_id,
                    "account_name": account_name,
                    "error": e,
                }
                stats.count(f"{function}.error", tags={"account_id": account_id})
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()
                raise

    log_data = {
        "function": function,
        "num_accounts": num_accounts,
        "num_roles": num_roles,
        "message": success_message,
    }
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=300)
def cache_policy_requests() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    requests = async_to_sync(cache_all_policy_requests)()

    log_data = {
        "function": function,
        "num_requests": len(requests),
        "message": "Successfully cached requests",
    }

    return log_data


@app.task(soft_time_limit=300)
def cache_cloud_account_mapping() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"

    account_mapping = async_to_sync(cache_cloud_accounts)()

    log_data = {
        "function": function,
        "num_accounts": len(account_mapping.accounts),
        "message": "Successfully cached cloud account mapping",
    }

    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_credential_authorization_mapping() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"

    authorization_mapping = async_to_sync(
        generate_and_store_credential_authorization_mapping
    )()

    log_data = {
        "function": function,
        "message": "Successfully cached cloud credential authorization mapping",
        "num_group_authorizations": len(authorization_mapping),
    }

    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_scps_across_organizations() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    scps = async_to_sync(cache_all_scps)()
    log_data = {
        "function": function,
        "message": "Successfully cached service control policies",
        "num_organizations": len(scps),
    }
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_organization_structure() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    org_structure = async_to_sync(cache_org_structure)()
    log_data = {
        "function": function,
        "message": "Successfully cached organization structure",
        "num_organizations": len(org_structure),
    }
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_resource_templates_task() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    templated_file_array = async_to_sync(cache_resource_templates)()
    log_data = {
        "function": function,
        "message": "Successfully cached resource templates",
        "num_templated_files": len(templated_file_array.templated_resources),
    }
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_self_service_typeahead_task() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    self_service_typeahead = async_to_sync(cache_self_service_typeahead)()
    log_data = {
        "function": function,
        "message": "Successfully cached resource templates",
        "num_templated_files": len(self_service_typeahead.typeahead_entries),
    }
    log.debug(log_data)
    return log_data


schedule_30_minute = timedelta(seconds=1800)
schedule_45_minute = timedelta(seconds=2700)
schedule_6_hours = timedelta(hours=6)
schedule_minute = timedelta(minutes=1)
schedule_5_minutes = timedelta(minutes=5)
schedule_24_hours = timedelta(hours=24)
schedule_1_hour = timedelta(hours=1)

if config.get("development", False):
    # If debug mode, we will set up the schedule to run the next minute after the job starts
    time_to_start = datetime.utcnow() + timedelta(minutes=1)
    dev_schedule = crontab(hour=time_to_start.hour, minute=time_to_start.minute)
    schedule_30_minute = dev_schedule
    schedule_45_minute = dev_schedule
    schedule_1_hour = dev_schedule
    schedule_6_hours = dev_schedule
    schedule_5_minutes = dev_schedule

schedule = {
    "cache_roles_across_accounts": {
        "task": "consoleme.celery_tasks.celery_tasks.cache_roles_across_accounts",
        "options": {"expires": 1000},
        "schedule": schedule_45_minute,
    },
    "clear_old_redis_iam_cache": {
        "task": "consoleme.celery_tasks.celery_tasks.clear_old_redis_iam_cache",
        "options": {"expires": 180},
        "schedule": schedule_6_hours,
    },
    "cache_policies_table_details": {
        "task": "consoleme.celery_tasks.celery_tasks.cache_policies_table_details",
        "options": {"expires": 1000},
        "schedule": schedule_30_minute,
    },
    "report_celery_last_success_metrics": {
        "task": "consoleme.celery_tasks.celery_tasks.report_celery_last_success_metrics",
        "options": {"expires": 60},
        "schedule": schedule_minute,
    },
    "cache_managed_policies_across_accounts": {
        "task": "consoleme.celery_tasks.celery_tasks.cache_managed_policies_across_accounts",
        "options": {"expires": 1000},
        "schedule": schedule_45_minute,
    },
    "cache_s3_buckets_across_accounts": {
        "task": "consoleme.celery_tasks.celery_tasks.cache_s3_buckets_across_accounts",
        "options": {"expires": 300},
        "schedule": schedule_45_minute,
    },
    "cache_sqs_queues_across_accounts": {
        "task": "consoleme.celery_tasks.celery_tasks.cache_sqs_queues_across_accounts",
        "options": {"expires": 300},
        "schedule": schedule_45_minute,
    },
    "cache_sns_topics_across_accounts": {
        "task": "consoleme.celery_tasks.celery_tasks.cache_sns_topics_across_accounts",
        "options": {"expires": 300},
        "schedule": schedule_45_minute,
    },
    "get_iam_role_limit": {
        "task": "consoleme.celery_tasks.celery_tasks.get_iam_role_limit",
        "options": {"expires": 300},
        "schedule": schedule_24_hours,
    },
    "cache_cloudtrail_errors_by_arn": {
        "task": "consoleme.celery_tasks.celery_tasks.cache_cloudtrail_errors_by_arn",
        "options": {"expires": 300},
        "schedule": schedule_1_hour,
    },
    "cache_resources_from_aws_config_across_accounts": {
        "task": "consoleme.celery_tasks.celery_tasks.cache_resources_from_aws_config_across_accounts",
        "options": {"expires": 300},
        "schedule": schedule_1_hour,
    },
    "cache_policy_requests": {
        "task": "consoleme.celery_tasks.celery_tasks.cache_policy_requests",
        "options": {"expires": 1000},
        "schedule": schedule_5_minutes,
    },
    "cache_cloud_account_mapping": {
        "task": "consoleme.celery_tasks.celery_tasks.cache_cloud_account_mapping",
        "options": {"expires": 1000},
        "schedule": schedule_1_hour,
    },
    "cache_credential_authorization_mapping": {
        "task": "consoleme.celery_tasks.celery_tasks.cache_credential_authorization_mapping",
        "options": {"expires": 1000},
        "schedule": schedule_5_minutes,
    },
    "cache_scps_across_organizations": {
        "task": "consoleme.celery_tasks.celery_tasks.cache_scps_across_organizations",
        "options": {"expires": 1000},
        "schedule": schedule_1_hour,
    },
    "cache_organization_structure": {
        "task": "consoleme.celery_tasks.celery_tasks.cache_organization_structure",
        "options": {"expires": 1000},
        "schedule": schedule_1_hour,
    },
    "cache_resource_templates_task": {
        "task": "consoleme.celery_tasks.celery_tasks.cache_resource_templates_task",
        "options": {"expires": 1000},
        "schedule": schedule_30_minute,
    },
    "cache_self_service_typeahead_task": {
        "task": "consoleme.celery_tasks.celery_tasks.cache_self_service_typeahead_task",
        "options": {"expires": 1000},
        "schedule": schedule_30_minute,
    },
}

if internal_celery_tasks and isinstance(internal_celery_tasks, dict):
    schedule = {**schedule, **internal_celery_tasks}

if config.get("celery.clear_tasks_for_development", False):
    schedule = {}

app.conf.beat_schedule = schedule
app.conf.timezone = "UTC"

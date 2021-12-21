"""
This module controls defines celery tasks and their applicable schedules. The celery beat server and workers will start
when invoked. Please add internal-only celery tasks to the celery_tasks plugin.

When ran in development mode (CONFIG_LOCATION=<location of development.yaml configuration file. To run both the celery
beat scheduler and a worker simultaneously, and to have jobs kick off starting at the next minute, run the following
command: celery -A consoleme.celery_tasks.celery_tasks worker --loglevel=info -l DEBUG -B

"""
from __future__ import absolute_import

import json  # We use a separate SetEncoder here so we cannot use ujson
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple, Union

import celery
import sentry_sdk
import ujson
from asgiref.sync import async_to_sync
from billiard.exceptions import SoftTimeLimitExceeded
from botocore.exceptions import ClientError
from celery import group
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
    allowed_to_sync_role,
    cache_all_scps,
    cache_org_structure,
    get_aws_principal_owner,
    get_enabled_regions_for_account,
    remove_temp_policies,
)
from consoleme.lib.aws_config import aws_config
from consoleme.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from consoleme.lib.cloud_credential_authorization_mapping import (
    generate_and_store_credential_authorization_mapping,
    generate_and_store_reverse_authorization_mapping,
)
from consoleme.lib.cloudtrail import CloudTrail
from consoleme.lib.dynamo import IAMRoleDynamoHandler, UserDynamoHandler
from consoleme.lib.event_bridge.access_denies import (
    detect_cloudtrail_denies_and_update_cache,
)
from consoleme.lib.event_bridge.role_updates import detect_role_changes_and_update_cache
from consoleme.lib.generic import un_wrap_json_and_dump_values
from consoleme.lib.git import store_iam_resources_in_git
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.policies import get_aws_config_history_url_for_resource
from consoleme.lib.redis import RedisHandler
from consoleme.lib.requests import cache_all_policy_requests
from consoleme.lib.self_service.typeahead import cache_self_service_typeahead
from consoleme.lib.templated_resources import cache_resource_templates
from consoleme.lib.timeout import Timeout
from consoleme.lib.v2.notifications import cache_notifications_to_redis_s3

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
    broker=config.get(
        f"celery.broker.{config.region}",
        config.get("celery.broker.global", "redis://127.0.0.1:6379/1"),
    ),
    backend=config.get(
        f"celery.backend.{config.region}",
        config.get("celery.broker.global", "redis://127.0.0.1:6379/2"),
    ),
)

if config.get("redis.use_redislite"):
    import tempfile

    import redislite

    redislite_db_path = os.path.join(
        config.get("redis.redislite.db_path", tempfile.NamedTemporaryFile().name)
    )
    redislite_client = redislite.Redis(redislite_db_path)
    redislite_socket_path = f"redis+socket://{redislite_client.socket_file}"
    app = Celery(
        "tasks",
        broker=f"{redislite_socket_path}?virtual_host=1",
        backend=f"{redislite_socket_path}?virtual_host=2",
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
            log.warning(log_data)
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
    log_data = {"function": f"{__name__}.{sys._getframe().f_code.co_name}", **tags}
    config.CONFIG.load_dynamic_config_from_redis(log_data, red)


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


def is_task_already_running(fun, args):
    """
    Returns True if an identical task for a given function (and arguments) is already being
    ran by Celery.
    """
    task_id = None
    if celery.current_task:
        task_id = celery.current_task.request.id
    if not task_id:
        return False
    log.debug(task_id)

    active_tasks = app.control.inspect()._request("active")
    if not active_tasks:
        return False
    for _, tasks in active_tasks.items():
        for task in tasks:
            if task.get("id") == task_id:
                continue
            if task.get("name") == fun and task.get("args") == args:
                return True
    return False


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
        red.hset(redis_key, str(role_entry["arn"]), str(json.dumps(role_entry)))
    except Exception as e:  # noqa
        stats.count(
            "_add_role_to_redis.error",
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


@app.task(soft_time_limit=7200)
def cache_cloudtrail_errors_by_arn() -> Dict:
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data: Dict = {"function": function}
    if is_task_already_running(function, []):
        log_data["message"] = "Skipping task: An identical task is currently running"
        log.debug(log_data)
        return log_data
    ct = CloudTrail()
    process_cloudtrail_errors_res: Dict = async_to_sync(ct.process_cloudtrail_errors)(
        aws
    )
    cloudtrail_errors = process_cloudtrail_errors_res["error_count_by_role"]
    red.setex(
        config.get(
            "celery.cache_cloudtrail_errors_by_arn.redis_key",
            "CLOUDTRAIL_ERRORS_BY_ARN",
        ),
        86400,
        json.dumps(cloudtrail_errors),
    )
    if process_cloudtrail_errors_res["num_new_or_changed_notifications"] > 0:
        cache_notifications.delay()
    log_data["number_of_roles_with_errors"]: len(cloudtrail_errors.keys())
    log_data["number_errors"]: sum(cloudtrail_errors.values())
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=1800)
def cache_policies_table_details() -> bool:
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

    # IAM Roles
    skip_iam_roles = config.get("cache_policies_table_details.skip_iam_roles", False)
    if not skip_iam_roles:
        all_iam_roles = async_to_sync(retrieve_json_data_from_redis_or_s3)(
            redis_key=config.get("aws.iamroles_redis_key", "IAM_ROLE_CACHE"),
            redis_data_type="hash",
            s3_bucket=config.get(
                "cache_iam_resources_across_accounts.all_roles_combined.s3.bucket"
            ),
            s3_key=config.get(
                "cache_iam_resources_across_accounts.all_roles_combined.s3.file",
                "account_resource_cache/cache_all_roles_v1.json.gz",
            ),
            default={},
        )

        for arn, role_details_j in all_iam_roles.items():
            role_details = ujson.loads(role_details_j)
            role_details_policy = ujson.loads(role_details.get("policy", {}))
            role_tags = role_details_policy.get("Tags", {})

            if not allowed_to_sync_role(arn, role_tags):
                continue

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
                    "technology": "AWS::IAM::Role",
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

    # IAM Users
    skip_iam_users = config.get("cache_policies_table_details.skip_iam_users", False)
    if not skip_iam_users:
        all_iam_users = async_to_sync(retrieve_json_data_from_redis_or_s3)(
            redis_key=config.get("aws.iamusers_redis_key", "IAM_USER_CACHE"),
            redis_data_type="hash",
            s3_bucket=config.get(
                "cache_iam_resources_across_accounts.all_users_combined.s3.bucket"
            ),
            s3_key=config.get(
                "cache_iam_resources_across_accounts.all_users_combined.s3.file",
                "account_resource_cache/cache_all_users_v1.json.gz",
            ),
            default={},
        )

        for arn, details_j in all_iam_users.items():
            details = ujson.loads(details_j)
            error_count = cloudtrail_errors.get(arn, 0)
            s3_errors_for_arn = s3_errors.get(arn, [])
            for error in s3_errors_for_arn:
                error_count += int(error.get("count"))
            account_id = arn.split(":")[4]
            account_name = accounts_d.get(str(account_id), "Unknown")
            resource_id = details.get("resourceId")
            items.append(
                {
                    "account_id": account_id,
                    "account_name": account_name,
                    "arn": arn,
                    "technology": "AWS::IAM::User",
                    "templated": red.hget(
                        config.get("templated_roles.redis_key", "TEMPLATED_ROLES_v2"),
                        arn.lower(),
                    ),
                    "errors": error_count,
                    "config_history_url": async_to_sync(
                        get_aws_config_history_url_for_resource
                    )(account_id, resource_id, arn, "AWS::IAM::User"),
                }
            )
    # S3 Buckets
    skip_s3_buckets = config.get("cache_policies_table_details.skip_s3_buckets", False)
    if not skip_s3_buckets:
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
                            "technology": "AWS::S3::Bucket",
                            "templated": None,
                            "errors": error_count,
                        }
                    )

    # SNS Topics
    skip_sns_topics = config.get("cache_policies_table_details.skip_sns_topics", False)
    if not skip_sns_topics:
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
                            "technology": "AWS::SNS::Topic",
                            "templated": None,
                            "errors": error_count,
                        }
                    )

    # SQS Queues
    skip_sqs_queues = config.get("cache_policies_table_details.skip_sqs_queues", False)
    if not skip_sqs_queues:
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
                            "technology": "AWS::SQS::Queue",
                            "templated": None,
                            "errors": error_count,
                        }
                    )

    # Managed Policies
    skip_managed_policies = config.get(
        "cache_policies_table_details.skip_managed_policies", False
    )
    if not skip_managed_policies:
        managed_policies_key: str = config.get(
            "redis.iam_managed_policies_key", "IAM_MANAGED_POLICIES"
        )
        managed_policies_accounts = red.hkeys(managed_policies_key)
        if managed_policies_accounts:
            for managed_policies_account in managed_policies_accounts:
                account_name = accounts_d.get(str(managed_policies_account), "Unknown")
                managed_policies_in_account = json.loads(
                    red.hget(managed_policies_key, managed_policies_account)
                )

                for policy_arn in managed_policies_in_account:
                    # managed policies that are managed by AWS shouldn't be added to the policies table for 2 reasons:
                    # 1. We don't manage them, can't edit them
                    # 2. There are a LOT of them and we would just end up spamming the policy table...
                    # TODO: discuss if this is okay
                    if str(managed_policies_account) not in policy_arn:
                        continue
                    error_count = 0
                    items.append(
                        {
                            "account_id": managed_policies_account,
                            "account_name": account_name,
                            "arn": policy_arn,
                            "technology": "managed_policy",
                            "templated": None,
                            "errors": error_count,
                        }
                    )

    # AWS Config Resources
    skip_aws_config_resources = config.get(
        "cache_policies_table_details.skip_aws_config_resources", False
    )
    if not skip_aws_config_resources:
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
                    "AWS::IAM::ManagedPolicy",
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
def cache_iam_resources_for_account(account_id: str) -> Dict[str, Any]:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {"function": function, "account_id": account_id}
    cache_keys = {
        "iam_roles": {
            "temp_cache_key": config.get(
                "aws.iamroles_redis_key_temp", "IAM_ROLE_CACHE_TEMP"
            )
        },
        "iam_users": {
            "temp_cache_key": config.get(
                "aws.iamusers_redis_key_temp", "IAM_USER_CACHE_TEMP"
            )
        },
        "iam_groups": {
            "temp_cache_key": config.get(
                "aws.iamgroups_redis_key_temp", "IAM_GROUP_CACHE_TEMP"
            )
        },
        "iam_policies": {
            "temp_cache_key": config.get(
                "aws.iampolicies_redis_key_temp", "IAM_POLICIES_CACHE_TEMP"
            )
        },
    }
    # Get the DynamoDB handler:
    dynamo = IAMRoleDynamoHandler()
    cache_key = config.get("aws.iamroles_redis_key", "IAM_ROLE_CACHE")
    # Only query IAM and put data in Dynamo if we're in the active region
    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev", "test"]:
        conn = dict(
            account_number=account_id,
            assume_role=config.get("policies.role_name"),
            region=config.region,
            client_kwargs=config.get("boto3.client_kwargs", {}),
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=config.get(
                    "aws.sts_endpoint_url", "https://sts.{region}.amazonaws.com"
                ).format(region=config.region),
            ),
        )
        client = boto3_cached_conn("iam", **conn)
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
        iam_users = all_iam_resources["UserDetailList"]
        iam_groups = all_iam_resources["GroupDetailList"]
        iam_policies = all_iam_resources["Policies"]

        # Make sure these roles satisfy config -> roles.allowed_*
        filtered_iam_roles = []
        for role in iam_roles:
            arn = role.get("Arn", "")
            tags = role.get("Tags", [])
            if allowed_to_sync_role(arn, tags):
                filtered_iam_roles.append(role)

        iam_roles = filtered_iam_roles

        if iam_roles:
            async_to_sync(store_json_results_in_redis_and_s3)(
                iam_roles,
                s3_bucket=config.get(
                    "cache_iam_resources_for_account.iam_roles.s3.bucket"
                ),
                s3_key=config.get(
                    "cache_iam_resources_for_account.iam_roles.s3.file",
                    "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
                ).format(resource_type="iam_roles", account_id=account_id),
            )
            log_data["num_iam_roles"] = len(iam_roles)

        if iam_users:
            async_to_sync(store_json_results_in_redis_and_s3)(
                iam_users,
                s3_bucket=config.get(
                    "cache_iam_resources_for_account.iam_users.s3.bucket"
                ),
                s3_key=config.get(
                    "cache_iam_resources_for_account.iam_users.s3.file",
                    "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
                ).format(resource_type="iam_users", account_id=account_id),
            )
            log_data["num_iam_users"] = len(iam_users)

        if iam_groups:
            async_to_sync(store_json_results_in_redis_and_s3)(
                iam_groups,
                s3_bucket=config.get(
                    "cache_iam_resources_for_account.iam_groups.s3.bucket"
                ),
                s3_key=config.get(
                    "cache_iam_resources_for_account.iam_groups.s3.file",
                    "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
                ).format(resource_type="iam_groups", account_id=account_id),
            )
            log_data["num_iam_groups"] = len(iam_groups)

        if iam_policies:
            async_to_sync(store_json_results_in_redis_and_s3)(
                iam_policies,
                s3_bucket=config.get(
                    "cache_iam_resources_for_account.iam_policies.s3.bucket"
                ),
                s3_key=config.get(
                    "cache_iam_resources_for_account.iam_policies.s3.file",
                    "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
                ).format(resource_type="iam_policies", account_id=account_id),
            )
            log_data["num_iam_policies"] = len(iam_policies)

        ttl: int = int((datetime.utcnow() + timedelta(hours=36)).timestamp())
        # Save them:
        for role in iam_roles:
            if remove_temp_policies(role, client):
                role = aws.get_iam_role_sync(account_id, role.get("RoleName", conn))
                async_to_sync(aws.cloudaux_to_aws)(role)
            role_entry = {
                "arn": role.get("Arn"),
                "name": role.get("RoleName"),
                "resourceId": role.get("RoleId"),
                "accountId": account_id,
                "ttl": ttl,
                "owner": get_aws_principal_owner(role),
                "policy": dynamo.convert_iam_resource_to_json(role),
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

        for user in iam_users:
            user_entry = {
                "arn": user.get("Arn"),
                "name": user.get("UserName"),
                "resourceId": user.get("UserId"),
                "accountId": account_id,
                "ttl": ttl,
                "owner": get_aws_principal_owner(user),
                "policy": dynamo.convert_iam_resource_to_json(user),
                "templated": False,  # Templates not supported for IAM users at this time
            }
            red.hset(
                cache_keys["iam_users"]["temp_cache_key"],
                str(user_entry["arn"]),
                str(json.dumps(user_entry)),
            )

        for g in iam_groups:
            group_entry = {
                "arn": g.get("Arn"),
                "name": g.get("GroupName"),
                "resourceId": g.get("GroupId"),
                "accountId": account_id,
                "ttl": ttl,
                "policy": dynamo.convert_iam_resource_to_json(g),
                "templated": False,  # Templates not supported for IAM groups at this time
            }
            red.hset(
                cache_keys["iam_groups"]["temp_cache_key"],
                str(group_entry["arn"]),
                str(json.dumps(group_entry)),
            )

        for policy in iam_policies:
            group_entry = {
                "arn": policy.get("Arn"),
                "name": policy.get("PolicyName"),
                "resourceId": policy.get("PolicyId"),
                "accountId": account_id,
                "ttl": ttl,
                "policy": dynamo.convert_iam_resource_to_json(policy),
                "templated": False,  # Templates not supported for IAM policies at this time
            }
            red.hset(
                cache_keys["iam_policies"]["temp_cache_key"],
                str(group_entry["arn"]),
                str(json.dumps(group_entry)),
            )

        # Maybe store all resources in git
        if config.get("cache_iam_resources_for_account.store_in_git.enabled"):
            store_iam_resources_in_git(all_iam_resources, account_id)

    stats.count(
        "cache_iam_resources_for_account.success", tags={"account_id": account_id}
    )
    log.debug({**log_data, "message": "Finished caching IAM resources for account"})
    return log_data


@app.task(soft_time_limit=3600)
def cache_iam_resources_across_accounts(
    run_subtasks: bool = True, wait_for_subtask_completion: bool = True
) -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"

    cache_keys = {
        "iam_roles": {
            "cache_key": config.get("aws.iamroles_redis_key", "IAM_ROLE_CACHE"),
            "temp_cache_key": config.get(
                "aws.iamroles_redis_key_temp", "IAM_ROLE_CACHE_TEMP"
            ),
        },
        "iam_users": {
            "cache_key": config.get("aws.iamusers_redis_key", "IAM_USER_CACHE"),
            "temp_cache_key": config.get(
                "aws.iamusers_redis_key_temp", "IAM_USER_CACHE_TEMP"
            ),
        },
        "iam_groups": {
            "cache_key": config.get("aws.iamgroups_redis_key", "IAM_GROUP_CACHE"),
            "temp_cache_key": config.get(
                "aws.iamgroups_redis_key_temp", "IAM_GROUP_CACHE_TEMP"
            ),
        },
        "iam_policies": {
            "cache_key": config.get("aws.iampolicies_redis_key", "IAM_POLICY_CACHE"),
            "temp_cache_key": config.get(
                "aws.iampolicies_redis_key_temp", "IAM_POLICIES_CACHE_TEMP"
            ),
        },
    }

    log_data = {"function": function, "cache_keys": cache_keys}
    if is_task_already_running(function, []):
        log_data["message"] = "Skipping task: An identical task is currently running"
        log.debug(log_data)
        return log_data

    # Remove stale temporary cache keys to ensure we receive fresh results. Don't remove stale cache keys if we're
    # running this as a part of `make redis` (`scripts/initialize_redis_oss.py`) because these cache keys are already
    # populated appropriately
    if run_subtasks and wait_for_subtask_completion:
        for k, v in cache_keys.items():
            temp_cache_key = v["temp_cache_key"]
            red.delete(temp_cache_key)

    accounts_d: Dict[str, str] = async_to_sync(get_account_id_to_name_mapping)()
    tasks = []
    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev"]:
        # First, get list of accounts
        # Second, call tasks to enumerate all the roles across all accounts
        for account_id in accounts_d.keys():
            if config.get("environment") in ["prod", "dev"]:
                tasks.append(cache_iam_resources_for_account.s(account_id))
            else:
                log.debug(
                    {
                        **log_data,
                        "message": (
                            "`environment` configuration is not set. Only running tasks for accounts in configuration "
                            "key `celery.test_account_ids`"
                        ),
                    }
                )
                if account_id in config.get("celery.test_account_ids", []):
                    tasks.append(cache_iam_resources_for_account.s(account_id))
        if run_subtasks:
            results = group(*tasks).apply_async()
            if wait_for_subtask_completion:
                # results.join() forces function to wait until all tasks are complete
                results.join(disable_sync_subtasks=False)
    else:
        log.debug(
            {
                **log_data,
                "message": (
                    "Running in non-active region. Caching roles from DynamoDB and not directly from AWS"
                ),
            }
        )
        dynamo = IAMRoleDynamoHandler()
        # In non-active regions, we just want to sync DDB data to Redis
        roles = dynamo.fetch_all_roles()
        for role_entry in roles:
            _add_role_to_redis(cache_keys["iam_roles"]["cache_key"], role_entry)

    # Delete roles in Redis cache with expired TTL
    all_roles = red.hgetall(cache_keys["iam_roles"]["cache_key"])
    roles_to_delete_from_cache = []
    for arn, role_entry_j in all_roles.items():
        role_entry = json.loads(role_entry_j)
        if datetime.fromtimestamp(role_entry["ttl"]) < datetime.utcnow():
            roles_to_delete_from_cache.append(arn)
    if roles_to_delete_from_cache:
        red.hdel(cache_keys["iam_roles"]["cache_key"], *roles_to_delete_from_cache)
        for arn in roles_to_delete_from_cache:
            all_roles.pop(arn, None)
    log_data["num_iam_roles"] = len(all_roles)
    # Store full list of roles in a single place. This list will be ~30 minutes out of date.
    if all_roles:
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_roles,
            redis_key=cache_keys["iam_roles"]["cache_key"],
            redis_data_type="hash",
            s3_bucket=config.get(
                "cache_iam_resources_across_accounts.all_roles_combined.s3.bucket"
            ),
            s3_key=config.get(
                "cache_iam_resources_across_accounts.all_roles_combined.s3.file",
                "account_resource_cache/cache_all_roles_v1.json.gz",
            ),
        )

    all_iam_users = red.hgetall(cache_keys["iam_users"]["temp_cache_key"])
    log_data["num_iam_users"] = len(all_iam_users)

    if all_iam_users:
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_iam_users,
            redis_key=cache_keys["iam_users"]["cache_key"],
            redis_data_type="hash",
            s3_bucket=config.get(
                "cache_iam_resources_across_accounts.all_users_combined.s3.bucket"
            ),
            s3_key=config.get(
                "cache_iam_resources_across_accounts.all_users_combined.s3.file",
                "account_resource_cache/cache_all_users_v1.json.gz",
            ),
        )

    # IAM Groups
    all_iam_groups = red.hgetall(cache_keys["iam_groups"]["temp_cache_key"])
    log_data["num_iam_groups"] = len(all_iam_groups)

    if all_iam_groups:
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_iam_groups,
            redis_key=cache_keys["iam_groups"]["cache_key"],
            redis_data_type="hash",
            s3_bucket=config.get(
                "cache_iam_resources_across_accounts.all_groups_combined.s3.bucket"
            ),
            s3_key=config.get(
                "cache_iam_resources_across_accounts.all_groups_combined.s3.file",
                "account_resource_cache/cache_all_groups_v1.json.gz",
            ),
        )

    # IAM Policies
    all_iam_policies = red.hgetall(cache_keys["iam_policies"]["temp_cache_key"])
    log_data["num_iam_policies"] = len(all_iam_groups)

    if all_iam_policies:
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_iam_policies,
            redis_key=cache_keys["iam_policies"]["cache_key"],
            redis_data_type="hash",
            s3_bucket=config.get(
                "cache_iam_resources_across_accounts.all_policies_combined.s3.bucket"
            ),
            s3_key=config.get(
                "cache_iam_resources_across_accounts.all_policies_combined.s3.file",
                "account_resource_cache/cache_all_policies_v1.json.gz",
            ),
        )

    # Remove temporary cache keys that were populated by the `cache_iam_resources_for_account(account_id)` tasks
    for k, v in cache_keys.items():
        temp_cache_key = v["temp_cache_key"]
        red.delete(temp_cache_key)

    stats.count(f"{function}.success")
    log_data["num_accounts"] = len(accounts_d)
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_managed_policies_for_account(account_id: str) -> Dict[str, Union[str, int]]:
    managed_policies: List[Dict] = get_all_managed_policies(
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        region=config.region,
        client_kwargs=config.get("boto3.client_kwargs", {}),
    )
    all_policies: List = []
    for policy in managed_policies:
        all_policies.append(policy.get("Arn"))

    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "account_id": account_id,
        "message": "Successfully cached IAM managed policies for account",
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


@app.task(soft_time_limit=3600)
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


@app.task(soft_time_limit=3600)
def cache_s3_buckets_across_accounts(
    run_subtasks: bool = True, wait_for_subtask_completion: bool = True
) -> Dict[str, Any]:
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    s3_bucket_redis_key: str = config.get("redis.s3_buckets_key", "S3_BUCKETS")
    s3_bucket = config.get("account_resource_cache.s3_combined.bucket")
    s3_key = config.get(
        "account_resource_cache.s3_combined.file",
        "account_resource_cache/cache_s3_combined_v1.json.gz",
    )

    accounts_d: Dict[str, str] = async_to_sync(get_account_id_to_name_mapping)()
    log_data = {
        "function": function,
        "num_accounts": len(accounts_d.keys()),
        "run_subtasks": run_subtasks,
        "wait_for_subtask_completion": wait_for_subtask_completion,
    }
    tasks = []
    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev"]:
        # Call tasks to enumerate all S3 buckets across all accounts
        for account_id in accounts_d.keys():
            if config.get("environment") in ["prod", "dev"]:
                tasks.append(cache_s3_buckets_for_account.s(account_id))
            else:
                if account_id in config.get("celery.test_account_ids", []):
                    tasks.append(cache_s3_buckets_for_account.s(account_id))
    log_data["num_tasks"] = len(tasks)
    if tasks and run_subtasks:
        results = group(*tasks).apply_async()
        if wait_for_subtask_completion:
            # results.join() forces function to wait until all tasks are complete
            results.join(disable_sync_subtasks=False)
    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev", "test"]:
        all_buckets = red.hgetall(s3_bucket_redis_key)
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_buckets, s3_bucket=s3_bucket, s3_key=s3_key
        )
    else:
        redis_result_set = async_to_sync(retrieve_json_data_from_redis_or_s3)(
            s3_bucket=s3_bucket, s3_key=s3_key
        )
        async_to_sync(store_json_results_in_redis_and_s3)(
            redis_result_set,
            redis_key=s3_bucket_redis_key,
            redis_data_type="hash",
        )
    log.debug(
        {**log_data, "message": "Successfully cached s3 buckets across known accounts"}
    )
    stats.count(f"{function}.success")
    return log_data


@app.task(soft_time_limit=3600)
def cache_sqs_queues_across_accounts(
    run_subtasks: bool = True, wait_for_subtask_completion: bool = True
) -> Dict[str, Any]:
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    sqs_queue_redis_key: str = config.get("redis.sqs_queues_key", "SQS_QUEUES")
    s3_bucket = config.get("account_resource_cache.sqs_combined.bucket")
    s3_key = config.get(
        "account_resource_cache.sqs_combined.file",
        "account_resource_cache/cache_sqs_queues_combined_v1.json.gz",
    )

    accounts_d: Dict[str, str] = async_to_sync(get_account_id_to_name_mapping)()
    log_data = {
        "function": function,
        "num_accounts": len(accounts_d.keys()),
        "run_subtasks": run_subtasks,
        "wait_for_subtask_completion": wait_for_subtask_completion,
    }
    tasks = []
    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev"]:
        for account_id in accounts_d.keys():
            if config.get("environment") in ["prod", "dev"]:
                tasks.append(cache_sqs_queues_for_account.s(account_id))
            else:
                if account_id in config.get("celery.test_account_ids", []):
                    tasks.append(cache_sqs_queues_for_account.s(account_id))
    log_data["num_tasks"] = len(tasks)
    if tasks and run_subtasks:
        results = group(*tasks).apply_async()
        if wait_for_subtask_completion:
            # results.join() forces function to wait until all tasks are complete
            results.join(disable_sync_subtasks=False)
    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev", "test"]:
        all_queues = red.hgetall(sqs_queue_redis_key)
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_queues, s3_bucket=s3_bucket, s3_key=s3_key
        )
    else:
        redis_result_set = async_to_sync(retrieve_json_data_from_redis_or_s3)(
            s3_bucket=s3_bucket, s3_key=s3_key
        )
        async_to_sync(store_json_results_in_redis_and_s3)(
            redis_result_set,
            redis_key=sqs_queue_redis_key,
            redis_data_type="hash",
        )
    log.debug(
        {**log_data, "message": "Successfully cached SQS queues across known accounts"}
    )
    stats.count(f"{function}.success")
    return log_data


@app.task(soft_time_limit=3600)
def cache_sns_topics_across_accounts(
    run_subtasks: bool = True, wait_for_subtask_completion: bool = True
) -> Dict[str, Any]:
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    sns_topic_redis_key: str = config.get("redis.sns_topics_key", "SNS_TOPICS")
    s3_bucket = config.get("account_resource_cache.sns_topics_combined.bucket")
    s3_key = config.get(
        "account_resource_cache.{resource_type}_topics_combined.file",
        "account_resource_cache/cache_{resource_type}_combined_v1.json.gz",
    ).format(resource_type="sns_topics")

    # First, get list of accounts
    accounts_d: Dict[str, str] = async_to_sync(get_account_id_to_name_mapping)()
    log_data = {
        "function": function,
        "num_accounts": len(accounts_d.keys()),
        "run_subtasks": run_subtasks,
        "wait_for_subtask_completion": wait_for_subtask_completion,
    }
    tasks = []
    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev"]:
        for account_id in accounts_d.keys():
            if config.get("environment") in ["prod", "dev"]:
                tasks.append(cache_sns_topics_for_account.s(account_id))
            else:
                if account_id in config.get("celery.test_account_ids", []):
                    tasks.append(cache_sns_topics_for_account.s(account_id))
    log_data["num_tasks"] = len(tasks)
    if tasks and run_subtasks:
        results = group(*tasks).apply_async()
        if wait_for_subtask_completion:
            # results.join() forces function to wait until all tasks are complete
            results.join(disable_sync_subtasks=False)
    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev", "test"]:
        all_topics = red.hgetall(sns_topic_redis_key)
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_topics, s3_bucket=s3_bucket, s3_key=s3_key
        )
    else:
        redis_result_set = async_to_sync(retrieve_json_data_from_redis_or_s3)(
            s3_bucket=s3_bucket, s3_key=s3_key
        )
        async_to_sync(store_json_results_in_redis_and_s3)(
            redis_result_set,
            redis_key=sns_topic_redis_key,
            redis_data_type="hash",
        )
    log.debug(
        {**log_data, "message": "Successfully cached SNS topics across known accounts"}
    )
    stats.count(f"{function}.success")
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_sqs_queues_for_account(account_id: str) -> Dict[str, Union[str, int]]:
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "account_id": account_id,
    }
    all_queues: set = set()
    enabled_regions = async_to_sync(get_enabled_regions_for_account)(account_id)
    for region in enabled_regions:
        try:
            client = boto3_cached_conn(
                "sqs",
                account_number=account_id,
                assume_role=config.get("policies.role_name"),
                region=region,
                read_only=True,
                sts_client_kwargs=dict(
                    region_name=config.region,
                    endpoint_url=config.get(
                        "aws.sts_endpoint_url", "https://sts.{region}.amazonaws.com"
                    ).format(region=config.region),
                ),
                client_kwargs=config.get("boto3.client_kwargs", {}),
            )

            paginator = client.get_paginator("list_queues")

            response_iterator = paginator.paginate(PaginationConfig={"PageSize": 1000})

            for res in response_iterator:
                for queue in res.get("QueueUrls", []):
                    arn = f"arn:aws:sqs:{region}:{account_id}:{queue.split('/')[4]}"
                    all_queues.add(arn)
        except Exception as e:
            log.error(
                {
                    **log_data,
                    "region": region,
                    "message": "Unable to sync SQS queues from region",
                    "error": str(e),
                }
            )
            sentry_sdk.capture_exception()
    sqs_queue_key: str = config.get("redis.sqs_queues_key", "SQS_QUEUES")
    red.hset(sqs_queue_key, account_id, json.dumps(list(all_queues)))

    log_data["message"] = "Successfully cached SQS queues for account"
    log_data["number_sqs_queues"] = len(all_queues)
    log.debug(log_data)
    stats.count(
        "cache_sqs_queues_for_account",
        tags={"account_id": account_id, "number_sqs_queues": len(all_queues)},
    )

    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev", "test"]:
        s3_bucket = config.get("account_resource_cache.sqs.bucket")
        s3_key = config.get(
            "account_resource_cache.{resource_type}.file",
            "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
        ).format(resource_type="sqs_queues", account_id=account_id)
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_queues, s3_bucket=s3_bucket, s3_key=s3_key
        )
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_sns_topics_for_account(account_id: str) -> Dict[str, Union[str, int]]:
    # Make sure it is regional
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "account_id": account_id,
    }
    all_topics: set = set()
    enabled_regions = async_to_sync(get_enabled_regions_for_account)(account_id)
    for region in enabled_regions:
        try:
            topics = list_topics(
                account_number=account_id,
                assume_role=config.get("policies.role_name"),
                region=region,
                read_only=True,
                sts_client_kwargs=dict(
                    region_name=config.region,
                    endpoint_url=config.get(
                        "aws.sts_endpoint_url", "https://sts.{region}.amazonaws.com"
                    ).format(region=config.region),
                ),
                client_kwargs=config.get("boto3.client_kwargs", {}),
            )
            for topic in topics:
                all_topics.add(topic["TopicArn"])
        except Exception as e:
            log.error(
                {
                    **log_data,
                    "region": region,
                    "message": "Unable to sync SNS topics from region",
                    "error": str(e),
                }
            )
            sentry_sdk.capture_exception()

    sns_topic_key: str = config.get("redis.sns_topics_key", "SNS_TOPICS")
    red.hset(sns_topic_key, account_id, json.dumps(list(all_topics)))

    log_data["message"] = "Successfully cached SNS topics for account"
    log_data["number_sns_topics"] = len(all_topics)
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
        client_kwargs=config.get("boto3.client_kwargs", {}),
    )
    buckets: List = []
    for bucket in s3_buckets["Buckets"]:
        buckets.append(bucket["Name"])
    s3_bucket_key: str = config.get("redis.s3_buckets_key", "S3_BUCKETS")
    red.hset(s3_bucket_key, account_id, json.dumps(buckets))

    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "account_id": account_id,
        "message": "Successfully cached S3 buckets for account",
        "number_s3_buckets": len(buckets),
    }
    log.debug(log_data)
    stats.count(
        "cache_s3_buckets_for_account",
        tags={"account_id": account_id, "number_s3_buckets": len(buckets)},
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


@app.task(soft_time_limit=3600, **default_retry_kwargs)
def cache_resources_from_aws_config_for_account(account_id) -> dict:
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {
        "function": function,
        "account_id": account_id,
    }
    if not config.get(
        "celery.cache_resources_from_aws_config_across_accounts.enabled",
        config.get(
            f"celery.cache_resources_from_aws_config_for_account.{account_id}.enabled",
            True,
        ),
    ):
        log_data[
            "message"
        ] = "Skipping task: Caching resources from AWS Config is disabled."
        log.debug(log_data)
        return log_data

    s3_bucket = config.get("aws_config_cache.s3.bucket")
    s3_key = config.get(
        "aws_config_cache.s3.file", "aws_config_cache/cache_{account_id}_v1.json.gz"
    ).format(account_id=account_id)
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
                un_wrap_json_and_dump_values(redis_result_set),
                redis_key=config.get(
                    "aws_config_cache.redis_key", "AWSCONFIG_RESOURCE_CACHE"
                ),
                redis_data_type="hash",
                s3_bucket=s3_bucket,
                s3_key=s3_key,
            )

            if config.get(
                "celery.cache_resources_from_aws_config_across_accounts.dynamo_enabled",
                True,
            ):
                dynamo = UserDynamoHandler()
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
    log_data["message"] = "Successfully cached resources from AWS Config for account"
    log_data["number_resources_synced"] = len(redis_result_set)
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=3600)
def cache_resources_from_aws_config_across_accounts(
    run_subtasks: bool = True,
    wait_for_subtask_completion: bool = True,
) -> Dict[str, Union[Union[str, int], Any]]:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    resource_redis_cache_key = config.get(
        "aws_config_cache.redis_key", "AWSCONFIG_RESOURCE_CACHE"
    )
    log_data = {
        "function": function,
        "resource_redis_cache_key": resource_redis_cache_key,
    }

    if not config.get(
        "celery.cache_resources_from_aws_config_across_accounts.enabled", True
    ):
        log_data[
            "message"
        ] = "Skipping task: Caching resources from AWS Config is disabled."
        log.debug(log_data)
        return log_data

    tasks = []
    # First, get list of accounts
    accounts_d = async_to_sync(get_account_id_to_name_mapping)()
    # Second, call tasks to enumerate all the roles across all accounts
    for account_id in accounts_d.keys():
        if config.get("environment") in ["prod", "dev"]:
            tasks.append(cache_resources_from_aws_config_for_account.s(account_id))
        else:
            if account_id in config.get("celery.test_account_ids", []):
                tasks.append(cache_resources_from_aws_config_for_account.s(account_id))
    if tasks:
        if run_subtasks:
            results = group(*tasks).apply_async()
            if wait_for_subtask_completion:
                # results.join() forces function to wait until all tasks are complete
                results.join(disable_sync_subtasks=False)

    # Delete roles in Redis cache with expired TTL
    all_resources = red.hgetall(resource_redis_cache_key)
    if all_resources:
        expired_arns = []
        for arn, resource_entry_j in all_resources.items():
            resource_entry = ujson.loads(resource_entry_j)
            if datetime.fromtimestamp(resource_entry["ttl"]) < datetime.utcnow():
                expired_arns.append(arn)
        if expired_arns:
            for expired_arn in expired_arns:
                all_resources.pop(expired_arn, None)
            red.hdel(resource_redis_cache_key, *expired_arns)

        log_data["number_of_resources"] = len(all_resources)

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
    return log_data


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

        @sts_conn("iam", client_kwargs=config.get("boto3.client_kwargs", {}))
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
    log_data = {
        "function": function,
    }
    if is_task_already_running(function, []):
        log_data["message"] = "Skipping task: An identical task is currently running"
        log.debug(log_data)
        return log_data

    authorization_mapping = async_to_sync(
        generate_and_store_credential_authorization_mapping
    )()

    reverse_mapping = async_to_sync(generate_and_store_reverse_authorization_mapping)(
        authorization_mapping
    )

    log_data["num_group_authorizations"] = len(authorization_mapping)
    log_data["num_identities"] = len(reverse_mapping)
    log.debug(
        {
            **log_data,
            "message": "Successfully cached cloud credential authorization mapping",
        }
    )
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
        "message": "Successfully cached IAM principals and templates for self service typeahead",
        "num_typeahead_entries": len(self_service_typeahead.typeahead_entries),
    }
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def trigger_credential_mapping_refresh_from_role_changes():
    """
    This task triggers a role cache refresh for any role that a change was detected for. This feature requires an
    Event Bridge rule monitoring Cloudtrail for your accounts for IAM role mutation.

    This task will trigger a credential authorization refresh if any changes were detected.

    This task should run in all regions to force IAM roles to be refreshed in each region's cache on change.
    :return:
    """
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    if not config.get(
        "celery.trigger_credential_mapping_refresh_from_role_changes.enabled"
    ):
        return {
            "function": function,
            "message": "Not running Celery task because it is not enabled.",
        }
    roles_changed = detect_role_changes_and_update_cache(app)
    log_data = {
        "function": function,
        "message": "Successfully checked role changes",
        "num_roles_changed": len(roles_changed),
    }
    if roles_changed:
        # Trigger credential authorization mapping refresh. We don't want credential authorization mapping refreshes
        # running in parallel, so the cache_credential_authorization_mapping is protected to prevent parallel runs.
        # This task can run in parallel without negative impact.
        cache_credential_authorization_mapping.apply_async(countdown=30)
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=3600, **default_retry_kwargs)
def cache_cloudtrail_denies():
    """
    This task caches access denies reported by Cloudtrail. This feature requires an
    Event Bridge rule monitoring Cloudtrail for your accounts for access deny errors.
    """
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    if not (
        config.region == config.get("celery.active_region", config.region)
        or config.get("environment") in ["dev", "test"]
    ):
        return {
            "function": function,
            "message": "Not running Celery task in inactive region",
        }
    events = async_to_sync(detect_cloudtrail_denies_and_update_cache)(app)
    if events["new_events"] > 0:
        # Spawn off a task to cache errors by ARN for the UI
        cache_cloudtrail_errors_by_arn.delay()
    log_data = {
        "function": function,
        "message": "Successfully cached cloudtrail denies",
        # Total CT denies
        "num_cloudtrail_denies": events["num_events"],
        # "New" CT messages that we don't already have cached in Dynamo DB. Not a "repeated" error
        "num_new_cloudtrail_denies": events["new_events"],
    }
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=60, **default_retry_kwargs)
def refresh_iam_role(role_arn):
    """
    This task is called on demand to asynchronously refresh an AWS IAM role in Redis/DDB

    """
    account_id = role_arn.split(":")[4]
    async_to_sync(aws().fetch_iam_role)(
        account_id, role_arn, force_refresh=True, run_sync=True
    )


@app.task(soft_time_limit=600, **default_retry_kwargs)
def cache_notifications() -> Dict[str, Any]:
    """
    This task caches notifications to be shown to end-users based on their identity or group membership.
    """
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {"function": function}
    result = async_to_sync(cache_notifications_to_redis_s3)()
    log_data.update({**result, "message": "Successfully cached notifications"})
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
    "cache_iam_resources_across_accounts": {
        "task": "consoleme.celery_tasks.celery_tasks.cache_iam_resources_across_accounts",
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

if config.get("celery.trigger_credential_mapping_refresh_from_role_changes.enabled"):
    schedule["trigger_credential_mapping_refresh_from_role_changes"] = {
        "task": "consoleme.celery_tasks.celery_tasks.trigger_credential_mapping_refresh_from_role_changes",
        "options": {"expires": 300},
        "schedule": schedule_minute,
    }

if config.get("celery.cache_cloudtrail_denies.enabled"):
    schedule["cache_cloudtrail_denies"] = {
        "task": "consoleme.celery_tasks.celery_tasks.cache_cloudtrail_denies",
        "options": {"expires": 300},
        "schedule": schedule_minute,
    }
    schedule["cache_cloudtrail_errors_by_arn"] = {
        "task": "consoleme.celery_tasks.celery_tasks.cache_cloudtrail_errors_by_arn",
        "options": {"expires": 300},
        "schedule": schedule_1_hour,
    }


if internal_celery_tasks and isinstance(internal_celery_tasks, dict):
    schedule = {**schedule, **internal_celery_tasks}

if config.get("celery.clear_tasks_for_development", False):
    schedule = {}

app.conf.beat_schedule = schedule
app.conf.timezone = "UTC"

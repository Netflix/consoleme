"""
This module controls defines celery tasks and their applicable schedules. The celery beat server and workers will start
when invoked. Please add internal-only celery tasks to the celery_tasks plugin.

When ran in development mode (CONFIG_LOCATION=<location of development.yaml configuration file. To run both the celery
beat scheduler and a worker simultaneously, and to have jobs kick off starting at the next minute, run the following
command: celery -A consoleme.celery.celery_tasks worker --loglevel=info -l DEBUG -B

"""
import json  # We use a separate SetEncoder here so we cannot use ujson
import sys
import time
from datetime import datetime, timedelta

import celery
import raven
import ujson
from asgiref.sync import async_to_sync
from celery.schedules import crontab
from celery.signals import task_received, task_success, task_failure
from cloudaux.aws.iam import get_all_managed_policies, get_account_authorization_details, get_user_access_keys
from cloudaux.aws.s3 import list_buckets
from cloudaux.aws.sns import list_topics
from cloudaux.aws.sqs import list_queues
from raven.contrib.celery import register_signal, register_logger_signal
from retrying import retry

from consoleme.config import config
from consoleme.lib.aws import put_object
from consoleme.lib.dynamo import IAMRoleDynamoHandler, UserDynamoHandler
from consoleme.lib.groups import get_group_url
from consoleme.lib.json_encoder import SetEncoder
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.redis import RedisHandler
from consoleme.lib.requests import get_request_review_url
from consoleme.lib.ses import send_group_modification_notification

from typing import Dict, Tuple

region = config.region


class Celery(celery.Celery):
    def on_configure(self) -> None:
        sentry_dsn = config.get("sentry.dsn")
        if sentry_dsn:
            client = raven.Client(sentry_dsn)
            # register a custom filter to filter out duplicate logs
            register_logger_signal(client)
            # hook into the Celery error handler
            register_signal(client)


app = Celery(
    "tasks",
    broker=config.get(f"celery.broker.{region}", "redis://127.0.0.1:6379/1"),
    backend=config.get(f"celery.backend.{region}", "redis://127.0.0.1:6379/2"),
)

app.conf.result_expires = config.get("celery.result_expires", 60)

if config.get("celery.purge"):
    # Useful to clear celery queue in development
    app.control.purge()

log = config.get_logger()
red = async_to_sync(RedisHandler().redis)()
aws = get_plugin_by_name(config.get("plugins.aws"))
auth = get_plugin_by_name(config.get("plugins.auth"))()
group_mapping = get_plugin_by_name(config.get("plugins.group_mapping"))()
internal_celery_tasks = get_plugin_by_name(config.get("plugins.internal_celery_tasks"))
stats = get_plugin_by_name(config.get("plugins.metrics"))()
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
    with app.pool.acquire() as conn:
        number_of_pending_tasks = conn.default_channel.client.llen("celery")
        stats.gauge("celery.pending_tasks", number_of_pending_tasks)
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
    if request:
        task_name = request.name
        task_id = request.id
        receiver_hostname = request.hostname
    else:
        task_name = sender.name
        task_id = sender.request.id
        receiver_hostname = sender.request.hostname

    tags = {
        "task_name": task_name,
        "task_id": task_id,
        "sender_hostname": sender_hostname,
        "receiver_hostname": receiver_hostname,
    }
    if kwargs.get("exception"):
        tags["error"] = repr(kwargs["exception"])
    return tags


@task_received.connect
def report_number_pending_tasks(**kwargs):
    """
    Report the number of pending tasks to our metrics broker every time a task is published. This metric can be used
    for autoscaling workers.

    :param sender:
    :param headers:
    :param body:
    :param kwargs:
    :return:
    """
    stats.timer("celery.new_pending_task", tags=get_celery_request_tags(**kwargs))
    with app.pool.acquire() as conn:
        number_of_pending_tasks = conn.default_channel.client.llen("celery")
        stats.gauge("celery.pending_tasks", number_of_pending_tasks)


@task_success.connect
def report_succeessful_task(**kwargs):
    """
    Report a generic success metric as tasks to our metrics broker every time a task finished correctly.
    This metric can be used for autoscaling workers.

    :param sender:
    :param headers:
    :param body:
    :param kwargs:
    :return:
    """
    stats.timer("celery.successful_task", tags=get_celery_request_tags(**kwargs))


@task_failure.connect
def report_failed_task(**kwargs):
    """
    Report a generic failure metric as tasks to our metrics broker every time a task finished correctly.
    This metric can be used for alerting.

    :param sender:
    :param headers:
    :param body:
    :param kwargs:
    :return:
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "Message": "Celery Task Failure",
    }

    error_tags = get_celery_request_tags(**kwargs)

    log_data.update(error_tags)
    log.error(log_data)
    stats.timer("celery.failed_task", tags=error_tags)


@app.task(soft_time_limit=1800)
def alert_on_group_changes() -> dict:
    """
    This function will send an email when entities are added to a google group that is opted in to alerts.

    Google groups with an attribute set for 'alert_on_changes' will have memberships queried and cached. When
    new users or groups are added to the group, this job will alert e-mails specified in the value of the
    `alert_on_changes` attribute.
    """
    function = f"{__name__}.{sys._getframe().f_code.co_name}"

    # Query for groups with "alert_on_changes" <list of emails> attribute
    alert_groups = async_to_sync(auth.get_groups_with_attribute_name_value)(
        "alert_on_changes", None
    )

    log_data = {
        "function": function,
        "message": "Alerting stakeholders on group changes",
        "number_of_alert_groups": len(alert_groups),
    }
    log.debug(log_data)
    # Query these groups for memberships
    for group in alert_groups.keys():
        log_data["group"] = group
        group_info = async_to_sync(auth.get_group_info)(group)
        if not group_info:
            log_data["message"] = "No information found for group"
            log.error(log_data)
            stats.count(f"{function}.no_group_info", tags={"group": group})
            continue
        # Get redis memberships
        past_members_set = False
        group_members_key = (
            f"{config.get('redis.group_members_key', 'GROUP_MEMBERS')}-{group}"
        )
        past_members = red.get(group_members_key)
        if past_members:
            past_members = ujson.loads(past_members)
            past_members_set = True
        else:
            past_members = []

        # Get group memberships
        current_members = async_to_sync(auth.get_group_members)(group)

        added_members = []
        removed_members = []

        # Find newly removed members
        for past_member in past_members:
            match = False
            for current_member in current_members:
                if past_member.get("name") == current_member.get("name"):
                    match = True
                    break
            if not match:
                removed_members.append(past_member)

        # Find newly added members and their applicable Consoleme Access Request URLs
        if past_members_set:
            for current_member in current_members:
                match = False
                for past_member in past_members:
                    if current_member.get("name") == past_member.get("name"):
                        match = True
                        break

                if not match:
                    username = current_member.get("name")
                    dynamo = UserDynamoHandler(username)
                    # If membership is different than before, check user's approved requests from the group
                    dynamo_requests = dynamo.get_requests_by_user(
                        username, group=group, status="approved"
                    )
                    if dynamo_requests and len(dynamo_requests) == 1:
                        current_member["request_url"] = get_request_review_url(
                            dynamo_requests[0]["request_id"]
                        )
                    added_members.append(current_member)

        # Send an e-mail with membership changes only in the primary region
        if (
                config.region == config.get("celery.active_region")
                and config.get("environment") == "prod"
        ):
            if added_members and current_members:
                async_to_sync(send_group_modification_notification)(
                    group,
                    group_info.alert_on_changes,
                    added_members,
                    group_url=get_group_url(group),
                )
            elif added_members and not current_members:
                log_data[
                    "message"
                ] = "No current members in this group. Not sending alert."
                log_data["added_members"] = added_members
                log_data["group_info.alert_on_changes"] = group_info.alert_on_changes
                log.error(log_data)
                stats.count(f"{function}.no_current_members", tags={"group": group})

        # Log the added and removed members
        log_data["added_members"] = json.dumps(added_members)
        log_data["removed_members"] = json.dumps(removed_members)
        if added_members or removed_members:
            log.debug(log_data)
        # Update redis cache
        red.set(group_members_key, json.dumps(current_members))
    stats.count("alert_on_group_changes.success")
    red.set(f"{function}.last_success", int(time.time()))
    return log_data


@retry(
    stop_max_attempt_number=4,
    wait_exponential_multiplier=1000,
    wait_exponential_max=1000,
)
def _add_role_to_redis(redis_key: str, role_entry: dict) -> None:
    """
    This function will add IAM role data to redis so that policy details can be quickly retrieved by the policies
    endpoint.

    IAM role data is stored in the `redis_key` redis key by the role's ARN.

    Parameters
    ----------
    redis_key : str
        The redis key (hash)
    role_entry : dict
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


@app.task(soft_time_limit=180)
def cache_audit_table_details() -> bool:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    d = UserDynamoHandler("consoleme")
    entries = async_to_sync(d.get_all_audit_logs)()

    topic = config.get("redis.audit_log_key", "CM_AUDIT_LOGS")
    red.set(topic, json.dumps(entries))
    red.set(f"{function}.last_success", int(time.time()))
    return True


@app.task(soft_time_limit=1800)
def cache_policies_table_details() -> bool:
    arns = red.hkeys("IAM_ROLE_CACHE")
    items = []
    accounts_d = aws.get_account_ids_to_names()
    function = f"{__name__}.{sys._getframe().f_code.co_name}"

    cloudtrail_topic = config.get("redis.cloudtrail_errors", "CLOUDTRAIL_ERRORS")
    all_cloudtrail_errors = red.get(cloudtrail_topic)
    cloudtrail_errors = {}
    if all_cloudtrail_errors:
        cloudtrail_errors = json.loads(all_cloudtrail_errors)

    s3_error_topic = config.get("redis.s3_errors", "S3_ERRORS")
    all_s3_errors = red.get(s3_error_topic)
    s3_errors = {}
    if all_s3_errors:
        s3_errors = json.loads(all_s3_errors)

    for arn in arns:
        errors = cloudtrail_errors.get(arn, {})
        error_count = 0
        for _, c in errors.items():
            error_count += int(c.get("count"))

        s3_errors_for_arn = s3_errors.get(arn, [])
        error_count = 0
        for error in s3_errors_for_arn:
            error_count += int(error.get("count"))

        account_id = arn.split(":")[4]
        account_name = accounts_d.get(str(account_id), ["Unknown"])[0]
        items.append(
            {
                "account_id": account_id,
                "account_name": account_name,
                "arn": arn,
                "technology": "iam",
                "templated": red.hget("TEMPLATED_ROLES", arn.lower()),
                "errors": error_count,
            }
        )
    s3_bucket_key: str = config.get("redis.s3_bucket_key", "S3_BUCKETS")
    s3_accounts = red.hkeys(s3_bucket_key)
    if s3_accounts:
        for account in s3_accounts:
            account_name = accounts_d.get(str(account), ["Unknown"])[0]
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

    sns_topic_key: str = config.get("redis.sns_topics_key ", "SNS_TOPICS")
    sns_accounts = red.hkeys(sns_topic_key)
    if sns_accounts:
        for account in sns_accounts:
            account_name = accounts_d.get(str(account), ["Unknown"])[0]
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
            account_name = accounts_d.get(str(account), ["Unknown"])[0]
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

    items_json = json.dumps(items, cls=SetEncoder)
    red.set(config.get("policies.redis_policies_key", "ALL_POLICIES"), items_json)
    stats.count("cache_policies_table_details.success", tags={"num_roles": len(arns)})
    red.set(f"{function}.last_success", int(time.time()))
    return True


@app.task(name="cache_roles_for_account", soft_time_limit=1800)
def cache_roles_for_account(account_id: str) -> bool:
    # Get the DynamoDB handler:
    dynamo = IAMRoleDynamoHandler()
    cache_key = config.get("aws.iamroles_redis_key", "IAM_ROLE_CACHE")
    function = f"{__name__}.{sys._getframe().f_code.co_name}"

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

        ttl: int = int((datetime.utcnow() + timedelta(hours=36)).timestamp())

        # Save them:
        for role in iam_roles:
            role_entry = {
                "arn": role.get("Arn"),
                "name": role.get("RoleName"),
                "accountId": account_id,
                "ttl": ttl,
                "policy": dynamo.convert_role_to_json(role),
                "templated": red.hget("TEMPLATED_ROLES", role.get("Arn").lower()),
            }

            # DynamoDB:
            dynamo.sync_iam_role_for_account(role_entry)

            # Redis:
            _add_role_to_redis(cache_key, role_entry)

    stats.count("cache_roles_for_account.success", tags={"account_id": account_id})
    red.set(f"{function}.last_success", int(time.time()))
    return True


@app.task(soft_time_limit=1800)
def cache_roles_across_accounts() -> bool:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    if config.region == config.get("celery.active_region") or config.get(
            "unit_testing.override_true"
    ):
        # First, get list of accounts
        accounts_d = aws.get_account_ids_to_names()
        # Second, call tasks to enumerate all the roles across all accounts
        for account_id in accounts_d.keys():
            if config.get("environment") == "prod":
                cache_roles_for_account.delay(account_id)
            else:
                if account_id in config.get("celery.test_account_ids", []):
                    cache_roles_for_account.delay(account_id)
    else:
        cache_key = config.get("aws.iamroles_redis_key", "IAM_ROLE_CACHE")
        dynamo = IAMRoleDynamoHandler()
        # In non-active regions, we just want to sync DDB data to Redis
        roles = dynamo.fetch_all_roles()
        for role_entry in roles:
            _add_role_to_redis(cache_key, role_entry)

    stats.count(f"{function}.success")
    red.set(f"{function}.last_success", int(time.time()))
    return True


@app.task(soft_time_limit=1800)
def cache_managed_policies_for_account(account_id: str) -> bool:
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    managed_policies: list[dict] = get_all_managed_policies(
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        region=config.region,
    )
    all_policies: list = []
    for policy in managed_policies:
        all_policies.append(policy.get("Arn"))

    policy_key = config.get("redis.iam_managed_policies_key", "IAM_MANAGED_POLICIES")
    red.hset(policy_key, account_id, json.dumps(all_policies))
    red.set(f"{function}.last_success", int(time.time()))
    return True


@app.task(soft_time_limit=120)
def cache_managed_policies_across_accounts() -> bool:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    # First, get list of accounts
    accounts_d = aws.get_account_ids_to_names()
    # Second, call tasks to enumerate all the roles across all accounts
    for account_id in accounts_d.keys():
        if config.get("environment") == "prod":
            cache_managed_policies_for_account.delay(account_id)
        else:
            if account_id in config.get("celery.test_account_ids", []):
                cache_managed_policies_for_account.delay(account_id)

    stats.count(f"{function}.success")
    red.set(f"{function}.last_success", int(time.time()))
    return True


@app.task(soft_time_limit=120)
def cache_s3_buckets_across_accounts() -> bool:
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    # First, get list of accounts
    accounts_d: list = aws.get_account_ids_to_names()
    # Second, call tasks to enumerate all the roles across all accounts
    for account_id in accounts_d.keys():
        if config.get("environment") == "prod":
            cache_s3_buckets_for_account.delay(account_id)
        else:
            if account_id in config.get("celery.test_account_ids", []):
                cache_s3_buckets_for_account.delay(account_id)
    stats.count(f"{function}.success")
    red.set(f"{function}.last_success", int(time.time()))
    return True


@app.task(soft_time_limit=120)
def cache_sqs_queues_across_accounts() -> bool:
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    # First, get list of accounts
    accounts_d: list = aws.get_account_ids_to_names()
    # Second, call tasks to enumerate all the roles across all accounts
    for account_id in accounts_d.keys():
        if config.get("environment") == "prod":
            cache_sqs_queues_for_account.delay(account_id)
        else:
            if account_id in config.get("celery.test_account_ids", []):
                cache_sqs_queues_for_account.delay(account_id)
    stats.count(f"{function}.success")
    red.set(f"{function}.last_success", int(time.time()))
    return True


@app.task(soft_time_limit=120)
def cache_sns_topics_across_accounts() -> bool:
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    # First, get list of accounts
    accounts_d: list = aws.get_account_ids_to_names()
    for account_id in accounts_d.keys():
        if config.get("environment") == "prod":
            cache_sns_topics_for_account.delay(account_id)
        else:
            if account_id in config.get("celery.test_account_ids", []):
                cache_sns_topics_for_account.delay(account_id)
    stats.count(f"{function}.success")
    red.set(f"{function}.last_success", int(time.time()))
    return True


@app.task(soft_time_limit=1800)
def cache_sqs_queues_for_account(account_id: str) -> bool:
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    all_queues: set = set()
    for region in config.get("celery.sync_regions"):
        queues = list_queues(
            account_number=account_id,
            assume_role=config.get("policies.role_name"),
            region=region,
        )
        for queue in queues:
            arn = f"arn:aws:sqs:{region}:{account_id}:{queue.split('/')[4]}"
            all_queues.add(arn)
    sqs_queue_key: str = config.get("redis.sqs_queues_key", "SQS_QUEUES")
    red.hset(sqs_queue_key, account_id, json.dumps(list(all_queues)))
    red.set(f"{function}.last_success", int(time.time()))
    return True


@app.task(soft_time_limit=1800)
def cache_sns_topics_for_account(account_id: str) -> bool:
    # Make sure it is regional
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    all_topics: set = set()
    for region in config.get("celery.sync_regions"):
        topics = list_topics(
            account_number=account_id,
            assume_role=config.get("policies.role_name"),
            region=region,
        )
        for topic in topics:
            all_topics.add(topic["TopicArn"])
    sns_topic_key: str = config.get("redis.sns_topics_key", "SNS_TOPICS")
    red.hset(sns_topic_key, account_id, json.dumps(list(all_topics)))
    red.set(f"{function}.last_success", int(time.time()))
    return True


@app.task(soft_time_limit=1800)
def cache_s3_buckets_for_account(account_id: str) -> bool:
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    s3_buckets: list = list_buckets(
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        region=config.region,
    )
    buckets: list = []
    for bucket in s3_buckets["Buckets"]:
        buckets.append(bucket["Name"])
    s3_bucket_key: str = config.get("redis.s3_buckets_key", "S3_BUCKETS")
    red.hset(s3_bucket_key, account_id, json.dumps(buckets))
    red.set(f"{function}.last_success", int(time.time()))
    return True


@retry(
    stop_max_attempt_number=4,
    wait_exponential_multiplier=1000,
    wait_exponential_max=1000,
)
def _scan_redis_iam_cache(
        cache_key: str, index: int, count: int
) -> Tuple[int, Dict[str, str]]:
    return red.hscan(cache_key, index, count=count)


@retry(
    stop_max_attempt_number=4,
    wait_exponential_multiplier=1000,
    wait_exponential_max=1000,
)
def _delete_redis_iam_cache(cache_key: str, arn: str):
    red.hdel(cache_key, arn)


@app.task(soft_time_limit=1800)
def clear_old_redis_iam_cache() -> bool:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    # Do not run if this is not in the active region:
    if config.region != config.get("celery.active_region"):
        red.set(f"{function}.last_success", int(time.time()))
        return

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
        for arn in roles_to_expire:
            red.hdel(cache_key, arn)
    except:  # noqa
        log_data = {
            "function": function,
            "message": "Error deleting role from Redis for cache cleanup.",
            "arn": arn,
        }
        log.error(log_data, exc_info=True)
        raise

    stats.count(f"{function}.success", tags={"expired_roles": len(roles_to_expire)})
    red.set(f"{function}.last_success", int(time.time()))
    return True


@app.task(soft_time_limit=1800)
def get_inventory_of_iam_keys() -> dict:
    """
    This function will get all the AWS IAM Keys for all the IAM users in all the AWS accounts.
    - Create an Array of IAM Access key ID
    - Write this data to an S3 bucket
    """
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {
        "function": function,
        "message": "Get inventory of IAM Keys"
    }
    # First, get list of accounts
    key_data = []
    if not config.get("get_inventory_of_iam_keys.enabled"):
        stats.count(f"{function}.success")
        return {}
    if config.region == config.get("celery.active_region") and config.get("environment") == "prod":
            accounts_d: list = aws.get_account_ids_to_names()
            users: list = []
            for account_id in accounts_d.keys():
                try:
                    iam_users = get_account_authorization_details(
                        account_number=account_id,
                        assume_role=config.get("policies.role_name"),
                        region=config.region,
                        filter="User",
                    )

                    for user in iam_users:
                        kd = get_user_access_keys(account_number=account_id,
                                                  assume_role=config.get("policies.role_name"),
                                                  region=config.region, user=user)
                        for key_details in kd:
                            key_data.append(key_details.get("AccessKeyId"))
                except Exception as e:
                    log_data["error"] = e
                    log.error(log_data, exc_info=True)
            put_object(
                Bucket=config.get("get_inventory_of_iam_keys.bucket"),
                assume_role=config.get("get_inventory_of_iam_keys.assume_role"),
                account_number=config.get("get_inventory_of_iam_keys.account_number"),
                region=config.get("get_inventory_of_iam_keys.region"),
                Key=config.get("get_inventory_of_iam_keys.key"),
                Body=json.dumps(key_data),
                session_name=config.get("get_inventory_of_iam_keys.session_name")
            )
    log_data["total_iam_access_key_ids"] = len(key_data)
    log.debug(log_data)
    stats.count(f"{function}.success")
    return log_data


schedule_30_minute = timedelta(seconds=1800)
schedule_45_minute = timedelta(seconds=2700)
schedule_6_hours = timedelta(hours=6)
schedule_minute = timedelta(minutes=1)
schedule_5_minutes = timedelta(minutes=5)
schedule_24_hours = timedelta(hours=24)

if config.get("development", False):
    # If debug mode, we will set up the schedule to run the next minute after the job starts
    time_to_start = datetime.utcnow() + timedelta(minutes=1)
    dev_schedule = crontab(hour=time_to_start.hour, minute=time_to_start.minute)
    schedule_30_minute = dev_schedule
    schedule_45_minute = dev_schedule
    schedule_6_hours = dev_schedule

schedule = {
    "alert_on_group_changes": {
        "task": "consoleme.celery.celery_tasks.alert_on_group_changes",
        "options": {"expires": 600},
        "schedule": schedule_30_minute,
    },
    "cache_roles_across_accounts": {
        "task": "consoleme.celery.celery_tasks.cache_roles_across_accounts",
        "options": {"expires": 1800},
        "schedule": schedule_45_minute,
    },
    "clear_old_redis_iam_cache": {
        "task": "consoleme.celery.celery_tasks.clear_old_redis_iam_cache",
        "options": {"expires": 1000},
        "schedule": schedule_6_hours,
    },
    "cache_policies_table_details": {
        "task": "consoleme.celery.celery_tasks.cache_policies_table_details",
        "options": {"expires": 1000},
        "schedule": schedule_45_minute,
    },
    "report_celery_last_success_metrics": {
        "task": "consoleme.celery.celery_tasks.report_celery_last_success_metrics",
        "options": {"expires": 1000},
        "schedule": schedule_minute,
    },
    "cache_managed_policies_across_accounts": {
        "task": "consoleme.celery.celery_tasks.cache_managed_policies_across_accounts",
        "options": {"expires": 1000},
        "schedule": schedule_45_minute,
    },
    "cache_s3_buckets_across_accounts": {
        "task": "consoleme.celery.celery_tasks.cache_s3_buckets_across_accounts",
        "options": {"expires": 1000},
        "schedule": schedule_45_minute,
    },
    "cache_sqs_queues_across_accounts": {
        "task": "consoleme.celery.celery_tasks.cache_sqs_queues_across_accounts",
        "options": {"expires": 1000},
        "schedule": schedule_45_minute,
    },
    "cache_sns_topics_across_accounts": {
        "task": "consoleme.celery.celery_tasks.cache_sns_topics_across_accounts",
        "options": {"expires": 1000},
        "schedule": schedule_45_minute,
    },
    "cache_audit_table_details": {
        "task": "consoleme.celery.celery_tasks.cache_audit_table_details",
        "options": {"expires": 1000},
        "schedule": schedule_5_minutes,
    },
    "get_iam_access_key_id": {
        "task": "consoleme.celery.celery_tasks.get_inventory_of_iam_keys",
        "options": {"expires": 1000},
        "schedule": schedule_24_hours,
    },
}

if internal_celery_tasks and isinstance(internal_celery_tasks, dict):
    schedule = {**schedule, **internal_celery_tasks}

app.conf.beat_schedule = schedule
app.conf.timezone = "UTC"

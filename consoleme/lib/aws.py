import json
import sys
import time
from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional

import pytz
from asgiref.sync import sync_to_async
from botocore.exceptions import ClientError
from cloudaux import CloudAux
from cloudaux import sts_conn
from cloudaux.aws.decorators import rate_limited
from cloudaux.aws.s3 import get_bucket_policy, get_bucket_tagging
from cloudaux.aws.sns import get_topic_attributes
from cloudaux.aws.sqs import get_queue_attributes, get_queue_url, list_queue_tags
from cloudaux.aws.sts import boto3_cached_conn
from deepdiff import DeepDiff
from policy_sentry.util.arns import (
    get_account_from_arn,
    get_resource_from_arn,
    get_service_from_arn,
)

from consoleme.config import config
from consoleme.exceptions.exceptions import BackgroundCheckNotPassedException
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.redis import RedisHandler, redis_hgetall

ALL_IAM_MANAGED_POLICIES: dict = {}
ALL_IAM_MANAGED_POLICIES_LAST_UPDATE: int = 0

log = config.get_logger(__name__)
auth = get_plugin_by_name(config.get("plugins.auth"))()
stats = get_plugin_by_name(config.get("plugins.metrics"))()


@rate_limited()
def create_managed_policy(cloudaux, name, path, policy, description):
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "cloudaux": cloudaux,
        "name": name,
        "path": path,
        "policy": policy,
        "description": "description",
        "message": "Creating Managed Policy",
    }
    log.debug(log_data)

    cloudaux.call(
        "iam.client.create_policy",
        PolicyName=name,
        Path=path,
        PolicyDocument=json.dumps(policy, indent=2),
        Description=description,
    )


async def needs_updating(existing_policy, new_policy):
    diff = DeepDiff(
        existing_policy, new_policy, ignore_order=True, report_repetition=True
    )
    if diff:
        return True
    return False


async def update_managed_policy(cloudaux, policy_name, new_policy, policy_arn):
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "new_policy": new_policy,
        "policy_name": policy_name,
        "policy_arn": policy_arn,
        "message": "Updating managed policy",
    }
    log.debug(log_data)

    current_policy_versions = []
    default_policy_index = 0
    versions = await sync_to_async(cloudaux.call)(
        "iam.client.list_policy_versions", PolicyArn=policy_arn
    )
    for i, version in enumerate(versions.get("Versions", [])):
        if version["IsDefaultVersion"]:
            default_policy_index = i
        current_policy_versions.append(version)

    if len(current_policy_versions) == 5:
        # Want to make sure we don't pop the default version so arbitrarily set position to 1 if default ends
        # up being the last index position
        pop_position = 1 if default_policy_index == 4 else 4
        await sync_to_async(cloudaux.call)(
            "iam.client.delete_policy_version",
            PolicyArn=policy_arn,
            VersionId=current_policy_versions.pop(pop_position)["VersionId"],
        )

    await sync_to_async(cloudaux.call)(
        "iam.client.create_policy_version",
        PolicyArn=policy_arn,
        PolicyDocument=json.dumps(new_policy, indent=2),
        SetAsDefault=True,
    )


async def create_or_update_managed_policy(
    new_policy,
    policy_name,
    policy_arn,
    description,
    policy_path="/",
    existing_policy=None,
    **conn_details,
):
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "new_policy": new_policy,
        "policy_name": policy_name,
        "policy_arn": policy_arn,
        "description": description,
        "policy_path": policy_path,
        "existing_policy": existing_policy,
        "conn_details": conn_details,
    }

    ca = await sync_to_async(CloudAux)(**conn_details)

    if not existing_policy:
        log_data["message"] = "Policy does not exist. Creating"
        log.debug(log_data)
        await sync_to_async(create_managed_policy)(
            ca, policy_name, policy_path, new_policy, description
        )
        return

    log_data["message"] = "Policy exists and needs to be updated"
    log.debug(log_data)
    # Update the managed policy
    await update_managed_policy(ca, policy_name, new_policy, policy_arn)


async def get_all_iam_managed_policies_for_account(account_id):
    global ALL_IAM_MANAGED_POLICIES_LAST_UPDATE
    global ALL_IAM_MANAGED_POLICIES

    policy_key: str = config.get(
        "redis.iam_managed_policies_key", "IAM_MANAGED_POLICIES"
    )
    current_time = time.time()
    if current_time - ALL_IAM_MANAGED_POLICIES_LAST_UPDATE > 500:
        red = await RedisHandler().redis()
        ALL_IAM_MANAGED_POLICIES = await sync_to_async(red.hgetall)(policy_key)
        ALL_IAM_MANAGED_POLICIES_LAST_UPDATE = current_time
    return json.loads(ALL_IAM_MANAGED_POLICIES.get(account_id, "[]"))


async def get_resource_account(arn: str) -> str:
    """Return the AWS account ID that owns a resource.

    In most cases, this will pull the ID directly from the ARN. For S3, we do
    a lookup in Redis to get the account ID.
    """
    s3_bucket_key = config.get("redis.s3_bucket_key", "S3_BUCKETS")
    s3_buckets: Dict = await redis_hgetall(s3_bucket_key)

    resource_account: str = get_account_from_arn(arn)
    if resource_account:
        return resource_account

    resource_type: str = get_service_from_arn(arn)
    resource_name: str = get_resource_from_arn(arn)
    if resource_type == "s3":
        for k, v in s3_buckets.items():
            if resource_name in v:
                return k
    else:
        return ""


async def get_resource_policies(
    principal_arn: str, resource_actions: Dict[str, List[str]], account: str
) -> Dict:
    resource_policies: List[Dict] = []
    for resource_name, resource_info in resource_actions.items():
        if resource_info.get("account") != account:
            # This is a cross-account request. Might need a resource policy.
            resource_account: str = resource_info.get("account")
            resource_type: str = resource_info.get("type")
            resource_region: str = resource_info.get("region")
            try:
                details = await fetch_resource_details(
                    resource_account, resource_type, resource_name, resource_region
                )
            except ClientError:
                # We don't have access to this resource, so we can't get the policy.
                details = {}
            # Default to a blank policy
            old_policy = details.get(
                "Policy", {"Version": "2012-10-17", "Statement": []}
            )
            arns = resource_info.get("arns", [])
            actions = resource_info.get("actions", [])
            new_policy = await update_resource_policy(
                old_policy, principal_arn, arns, actions
            )

            result = {
                "resource": resource_name,
                "policy_document": new_policy,
            }
            resource_policies.append(result)

    return resource_policies


async def update_resource_policy(
    existing: Dict, principal_arn: str, resource_arns: List[str], actions: List[str]
) -> Dict:
    policy_dict = deepcopy(existing)
    new_statement = {
        "Effect": "Allow",
        "Principal": {"AWS": [principal_arn]},
        "Action": list(set(actions)),
        "Resource": resource_arns,
    }
    policy_dict["Statement"].append(new_statement)
    return policy_dict


async def fetch_resource_details(
    account_id: str, resource_type: str, resource_name: str, region: str
) -> dict:
    if resource_type == "s3":
        return await fetch_s3_bucket(account_id, resource_name)
    elif resource_type == "sqs":
        return await fetch_sqs_queue(account_id, region, resource_name)
    elif resource_type == "sns":
        return await fetch_sns_topic(account_id, region, resource_name)
    else:
        return {}


async def fetch_sns_topic(account_id: str, region: str, resource_name: str) -> dict:
    arn: str = f"arn:aws:sns:{region}:{account_id}:{resource_name}"
    client = await sync_to_async(boto3_cached_conn)(
        "sns",
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        region=region,
    )

    result: Dict = await sync_to_async(get_topic_attributes)(
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        TopicArn=arn,
        region=region,
    )

    tags: Dict = await sync_to_async(client.list_tags_for_resource)(ResourceArn=arn)
    result["TagSet"] = tags["Tags"]
    if not isinstance(result["Policy"], dict):
        result["Policy"] = json.loads(result["Policy"])
    return result


async def fetch_sqs_queue(account_id: str, region: str, resource_name: str) -> dict:
    queue_url: str = await sync_to_async(get_queue_url)(
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        region=region,
        QueueName=resource_name,
    )

    result: Dict = await sync_to_async(get_queue_attributes)(
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        region=region,
        QueueUrl=queue_url,
        AttributeNames=["Policy", "QueueArn"],
    )

    tags: Dict = await sync_to_async(list_queue_tags)(
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        region=region,
        QueueUrl=queue_url,
    )
    result["TagSet"]: list = []
    result["QueueUrl"]: str = queue_url
    if tags:
        result["TagSet"] = [{"Key": k, "Value": v} for k, v in tags.items()]

    return result


async def fetch_s3_bucket(account_id: str, bucket_name: str) -> dict:
    """Fetch S3 Bucket and applicable policies

        :param account_id:
        :param bucket_name:
        :return:
    """

    log_data: Dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "bucket_name": bucket_name,
        "account_id": account_id,
    }
    log.debug(log_data)

    try:
        policy: Dict = await sync_to_async(get_bucket_policy)(
            account_number=account_id,
            assume_role=config.get("policies.role_name"),
            region=config.region,
            Bucket=bucket_name,
        )
    except ClientError as e:
        if "NoSuchBucketPolicy" in str(e):
            policy = {"Policy": "{}"}
        else:
            raise
    try:
        tags: Dict = await sync_to_async(get_bucket_tagging)(
            account_number=account_id,
            assume_role=config.get("policies.role_name"),
            region=config.region,
            Bucket=bucket_name,
        )
    except ClientError as e:
        if "NoSuchTagSet" in str(e):
            tags = {"TagSet": []}
        else:
            raise

    result: Dict = {**policy, **tags}
    result["Policy"] = json.loads(result["Policy"])

    return result


async def raise_if_background_check_required_and_no_background_check(role, user):
    for compliance_account_id in config.get("aws.compliance_account_ids", []):
        if compliance_account_id == role.split(":")[4]:
            user_info = await auth.get_user_info(user, object=True)
            if not user_info.passed_background_check:
                function = f"{__name__}.{sys._getframe().f_code.co_name}"
                log_data: dict = {
                    "function": function,
                    "user": user,
                    "role": role,
                    "message": "User trying to access SEG role without background check",
                }
                log.error(log_data)
                stats.count(
                    f"{function}.access_denied_background_check_not_passed",
                    tags={"function": function, "user": user, "role": role},
                )
                raise BackgroundCheckNotPassedException(
                    config.get(
                        "aws.background_check_not_passed",
                        "You must have passed a background check to access role "
                        "{role}.",
                    ).format(role=role)
                )


@rate_limited()
@sts_conn("s3")
def put_object(client=None, **kwargs):
    """Create an S3 object -- calls wrapped with CloudAux."""
    client.put_object(**kwargs)


def apply_managed_policy_to_role(
    role: Dict, policy_name: str, session_name: str
) -> bool:
    """
    Apply a managed policy to a role.
    :param role: An AWS role dictionary (from a boto3 get_role or get_account_authorization_details call)
    :param policy_name: Name of managed policy to add to role
    :param session_name: Name of session to assume role with. This is an identifier that will be logged in CloudTrail
    :return:
    """
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {
        "function": function,
        "role": role,
        "policy_name": policy_name,
        "session_name": session_name,
    }
    account_id = role.get("Arn").split(":")[4]
    policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
    client = boto3_cached_conn(
        "iam",
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        session_name=session_name,
    )

    client.attach_role_policy(RoleName=role.get("RoleName"), PolicyArn=policy_arn)
    log_data["message"] = "Applied managed policy to role"
    log.debug(log_data)
    stats.count(
        f"{function}.attach_role_policy",
        tags={"role": role.get("Arn"), "policy": policy_arn},
    )
    return True


def role_has_tag(role: Dict, key: str, value: Optional[str] = None) -> bool:
    """
    Checks a role dictionary and determine of the role has the specified tag. If `value` is passed,
    This function will only return true if the tag's value matches the `value` variable.
    :param role: An AWS role dictionary (from a boto3 get_role or get_account_authorization_details call)
    :param key: key of the tag
    :param value: optional value of the tag
    :return:
    """
    for tag in role.get("Tags", []):
        if tag.get("Key") == key:
            if not value or tag.get("Value") == value:
                return True
    return False


def role_has_managed_policy(role: Dict, managed_policy_name: str) -> bool:
    """
    Checks a role dictionary to determine if a managed policy is attached
    :param role: An AWS role dictionary (from a boto3 get_role or get_account_authorization_details call)
    :param managed_policy_name: the name of the managed policy
    :return:
    """

    for managed_policy in role.get("AttachedManagedPolicies", []):
        if managed_policy.get("PolicyName") == managed_policy_name:
            return True
    return False


def role_newer_than_x_days(role: Dict, days: int) -> bool:
    """
    Checks a role dictionary to determine if it is newer than the specified number of days
    :param role:  An AWS role dictionary (from a boto3 get_role or get_account_authorization_details call)
    :param days: number of days
    :return:
    """
    role_age = datetime.now(tz=pytz.utc) - role.get("CreateDate")
    if role_age.days < days:
        return True
    return False


def is_role_instance_profile(role: Dict) -> bool:
    """
    Checks a role naively to determine if it is associate with an instance profile.
    We only check by name, and not the actual attached instance profiles.
    :param role: An AWS role dictionary (from a boto3 get_role or get_account_authorization_details call)
    :return:
    """
    return role.get("RoleName").endswith("InstanceProfile")

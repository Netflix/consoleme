import fnmatch
import json
import re
import sys
import time
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import boto3
import pytz
import sentry_sdk
from asgiref.sync import sync_to_async
from botocore.exceptions import ClientError, ParamValidationError
from cloudaux import CloudAux
from cloudaux.aws.decorators import rate_limited
from cloudaux.aws.iam import get_managed_policy_document, get_policy
from cloudaux.aws.s3 import (
    get_bucket_location,
    get_bucket_policy,
    get_bucket_resource,
    get_bucket_tagging,
)
from cloudaux.aws.sns import get_topic_attributes
from cloudaux.aws.sqs import get_queue_attributes, get_queue_url, list_queue_tags
from cloudaux.aws.sts import boto3_cached_conn
from dateutil.parser import parse
from deepdiff import DeepDiff
from parliament import analyze_policy_string, enhance_finding
from policy_sentry.util.arns import get_account_from_arn, parse_arn

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    BackgroundCheckNotPassedException,
    InvalidInvocationArgument,
    MissingConfigurationValue,
)
from consoleme.lib.account_indexers.aws_organizations import (
    retrieve_org_structure,
    retrieve_scps_for_organization,
)
from consoleme.lib.aws_config.aws_config import query
from consoleme.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from consoleme.lib.generic import sort_dict
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.redis import RedisHandler, redis_hget, redis_hgetex, redis_hsetex
from consoleme.models import (
    CloneRoleRequestModel,
    RoleCreationRequestModel,
    ServiceControlPolicyArrayModel,
    ServiceControlPolicyModel,
)

ALL_IAM_MANAGED_POLICIES: dict = {}
ALL_IAM_MANAGED_POLICIES_LAST_UPDATE: int = 0

log = config.get_logger(__name__)
auth = get_plugin_by_name(config.get("plugins.auth", "default_auth"))()
stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
red = RedisHandler().redis_sync()


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
    oldest_policy_version = -1
    oldest_timestamp = None
    for i, version in enumerate(versions.get("Versions", [])):
        if version["IsDefaultVersion"]:
            default_policy_index = i
        current_policy_versions.append(version)
        if oldest_policy_version == -1 or oldest_timestamp > version["CreateDate"]:
            oldest_policy_version = i
            oldest_timestamp = version["CreateDate"]

    if len(current_policy_versions) == 5:
        pop_position = oldest_policy_version
        # Want to make sure we don't pop the default version so arbitrarily set position to oldest + 1 mod N
        # if default is also the oldest
        if default_policy_index == oldest_policy_version:
            pop_position = (oldest_policy_version + 1) % len(current_policy_versions)
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

    if ALL_IAM_MANAGED_POLICIES:
        return json.loads(ALL_IAM_MANAGED_POLICIES.get(account_id, "[]"))
    else:
        s3_bucket = config.get("account_resource_cache.s3.bucket")
        s3_key = config.get(
            "account_resource_cache.s3.file",
            "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
        ).format(resource_type="managed_policies", account_id=account_id)
        return await retrieve_json_data_from_redis_or_s3(
            s3_bucket=s3_bucket, s3_key=s3_key, default=[]
        )


async def get_resource_account(arn: str) -> str:
    """Return the AWS account ID that owns a resource.

    In most cases, this will pull the ID directly from the ARN.
    If we are unsuccessful in pulling the account from ARN, we try to grab it from our resources cache
    """
    red = await RedisHandler().redis()
    resource_account: str = get_account_from_arn(arn)
    if resource_account:
        return resource_account

    resources_from_aws_config_redis_key: str = config.get(
        "aws_config_cache.redis_key", "AWSCONFIG_RESOURCE_CACHE"
    )

    if not red.exists(resources_from_aws_config_redis_key):
        # This will force a refresh of our redis cache if the data exists in S3
        await retrieve_json_data_from_redis_or_s3(
            redis_key=resources_from_aws_config_redis_key,
            s3_bucket=config.get("aws_config_cache_combined.s3.bucket"),
            s3_key=config.get(
                "aws_config_cache_combined.s3.file",
                "aws_config_cache_combined/aws_config_resource_cache_combined_v1.json.gz",
            ),
            redis_data_type="hash",
        )

    resource_info = await redis_hget(resources_from_aws_config_redis_key, arn)
    if resource_info:
        return json.loads(resource_info).get("accountId", "")
    elif "arn:aws:s3:::" in arn:
        # Try to retrieve S3 bucket information from S3 cache. This is inefficient and we should ideally have
        # retrieved this info from our AWS Config cache, but we've encountered problems with AWS Config historically
        # that have necessitated this code.
        s3_cache = await retrieve_json_data_from_redis_or_s3(
            redis_key=config.get("redis.s3_buckets_key", "S3_BUCKETS"),
            redis_data_type="hash",
        )
        search_bucket_name = arn.split(":")[-1]
        for bucket_account_id, buckets in s3_cache.items():
            buckets_j = json.loads(buckets)
            if search_bucket_name in buckets_j:
                return bucket_account_id
    return ""


async def get_resource_policy(account: str, resource_type: str, name: str, region: str):
    try:
        details = await fetch_resource_details(account, resource_type, name, region)
    except ClientError:
        # We don't have access to this resource, so we can't get the policy.
        details = {}

    # Default policy
    default_policy = {"Version": "2012-10-17", "Statement": []}

    # When NoSuchBucketPolicy, the above method returns {"Policy": {}}, so we default to blank policy
    if "Policy" in details and "Statement" not in details["Policy"]:
        details = {"Policy": default_policy}

    # Default to a blank policy
    return details.get("Policy", default_policy)


async def get_resource_policies(
    principal_arn: str, resource_actions: Dict[str, Dict[str, Any]], account: str
) -> Tuple[List[Dict], bool]:
    resource_policies: List[Dict] = []
    cross_account_request: bool = False
    for resource_name, resource_info in resource_actions.items():
        resource_account: str = resource_info.get("account", "")
        if resource_account and resource_account != account:
            # This is a cross-account request. Might need a resource policy.
            cross_account_request = True
            resource_type: str = resource_info.get("type", "")
            resource_region: str = resource_info.get("region", "")
            old_policy = await get_resource_policy(
                resource_account, resource_type, resource_name, resource_region
            )
            arns = resource_info.get("arns", [])
            actions = resource_info.get("actions", [])
            new_policy = await generate_updated_resource_policy(
                old_policy, principal_arn, arns, actions
            )

            result = {
                "resource": resource_name,
                "account": resource_account,
                "type": resource_type,
                "region": resource_region,
                "policy_document": new_policy,
            }
            resource_policies.append(result)

    return resource_policies, cross_account_request


async def generate_updated_resource_policy(
    existing: Dict,
    principal_arn: str,
    resource_arns: List[str],
    actions: List[str],
    include_resources: bool = True,
) -> Dict:
    """

    :param existing: Dict: the current existing policy document
    :param principal_arn: the Principal ARN which wants access to the resource
    :param resource_arns: the Resource ARNs
    :param actions: The list of Actions to be added
    :param include_resources: whether to include resources in the new statement or not
    :return: Dict: generated updated resource policy that includes a new statement for the listed actions
    """
    policy_dict = deepcopy(existing)
    new_statement = {
        "Effect": "Allow",
        "Principal": {"AWS": [principal_arn]},
        "Action": list(set(actions)),
    }
    if include_resources:
        new_statement["Resource"] = resource_arns
    policy_dict["Statement"].append(new_statement)
    return policy_dict


async def fetch_resource_details(
    account_id: str,
    resource_type: str,
    resource_name: str,
    region: str,
    path: str = None,
) -> dict:
    if resource_type == "s3":
        return await fetch_s3_bucket(account_id, resource_name)
    elif resource_type == "sqs":
        return await fetch_sqs_queue(account_id, region, resource_name)
    elif resource_type == "sns":
        return await fetch_sns_topic(account_id, region, resource_name)
    elif resource_type == "managed_policy":
        return await fetch_managed_policy_details(account_id, resource_name, path)
    else:
        return {}


async def fetch_managed_policy_details(
    account_id: str, resource_name: str, path: str = None
) -> Optional[Dict]:
    from consoleme.lib.policies import get_aws_config_history_url_for_resource

    if path:
        resource_name = path + "/" + resource_name
    policy_arn: str = f"arn:aws:iam::{account_id}:policy/{resource_name}"
    result: Dict = {}
    result["Policy"] = await sync_to_async(get_managed_policy_document)(
        policy_arn=policy_arn,
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        region=config.region,
        retry_max_attempts=2,
        client_kwargs=config.get("boto3.client_kwargs", {}),
    )
    policy_details = await sync_to_async(get_policy)(
        policy_arn=policy_arn,
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        region=config.region,
        retry_max_attempts=2,
        client_kwargs=config.get("boto3.client_kwargs", {}),
    )

    try:
        result["TagSet"] = policy_details["Policy"]["Tags"]
    except KeyError:
        result["TagSet"] = []
    result["config_timeline_url"] = await get_aws_config_history_url_for_resource(
        account_id,
        policy_arn,
        resource_name,
        "AWS::IAM::ManagedPolicy",
        region=config.region,
    )

    return result


async def fetch_assume_role_policy(role_arn: str) -> Optional[Dict]:
    account_id = role_arn.split(":")[4]
    role_name = role_arn.split("/")[-1]
    try:
        role = await fetch_role_details(account_id, role_name)
    except ClientError:
        # Role is most likely on an account that we do not have access to
        sentry_sdk.capture_exception()
        return None
    return role.assume_role_policy_document


async def fetch_sns_topic(account_id: str, region: str, resource_name: str) -> dict:
    from consoleme.lib.policies import get_aws_config_history_url_for_resource

    regions = await get_enabled_regions_for_account(account_id)
    if region not in regions:
        raise InvalidInvocationArgument(
            f"Region '{region}' is not valid region on account '{account_id}'."
        )

    arn: str = f"arn:aws:sns:{region}:{account_id}:{resource_name}"
    client = await sync_to_async(boto3_cached_conn)(
        "sns",
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        region=region,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=config.get(
                "aws.sts_endpoint_url", "https://sts.{region}.amazonaws.com"
            ).format(region=config.region),
        ),
        client_kwargs=config.get("boto3.client_kwargs", {}),
        retry_max_attempts=2,
    )

    result: Dict = await sync_to_async(get_topic_attributes)(
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        TopicArn=arn,
        region=region,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=config.get(
                "aws.sts_endpoint_url", "https://sts.{region}.amazonaws.com"
            ).format(region=config.region),
        ),
        client_kwargs=config.get("boto3.client_kwargs", {}),
        retry_max_attempts=2,
    )

    tags: Dict = await sync_to_async(client.list_tags_for_resource)(ResourceArn=arn)
    result["TagSet"] = tags["Tags"]
    if not isinstance(result["Policy"], dict):
        result["Policy"] = json.loads(result["Policy"])

    result["config_timeline_url"] = await get_aws_config_history_url_for_resource(
        account_id,
        arn,
        resource_name,
        "AWS::SNS::Topic",
        region=region,
    )
    return result


async def fetch_sqs_queue(account_id: str, region: str, resource_name: str) -> dict:
    from consoleme.lib.policies import get_aws_config_history_url_for_resource

    regions = await get_enabled_regions_for_account(account_id)
    if region not in regions:
        raise InvalidInvocationArgument(
            f"Region '{region}' is not valid region on account '{account_id}'."
        )

    queue_url: str = await sync_to_async(get_queue_url)(
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        region=region,
        QueueName=resource_name,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=config.get(
                "aws.sts_endpoint_url", "https://sts.{region}.amazonaws.com"
            ).format(region=config.region),
        ),
        client_kwargs=config.get("boto3.client_kwargs", {}),
        retry_max_attempts=2,
    )

    result: Dict = await sync_to_async(get_queue_attributes)(
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        region=region,
        QueueUrl=queue_url,
        AttributeNames=["All"],
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=config.get(
                "aws.sts_endpoint_url", "https://sts.{region}.amazonaws.com"
            ).format(region=config.region),
        ),
        client_kwargs=config.get("boto3.client_kwargs", {}),
        retry_max_attempts=2,
    )

    tags: Dict = await sync_to_async(list_queue_tags)(
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        region=region,
        QueueUrl=queue_url,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=config.get(
                "aws.sts_endpoint_url", "https://sts.{region}.amazonaws.com"
            ).format(region=config.region),
        ),
        client_kwargs=config.get("boto3.client_kwargs", {}),
        retry_max_attempts=2,
    )
    result["TagSet"]: list = []
    result["QueueUrl"]: str = queue_url
    if tags:
        result["TagSet"] = [{"Key": k, "Value": v} for k, v in tags.items()]
    if result.get("CreatedTimestamp"):
        result["created_time"] = datetime.utcfromtimestamp(
            int(float(result["CreatedTimestamp"]))
        ).isoformat()
    if result.get("LastModifiedTimestamp"):
        result["updated_time"] = datetime.utcfromtimestamp(
            int(float(result["LastModifiedTimestamp"]))
        ).isoformat()
    # Unfortunately, the queue_url we get from our `get_queue_url` call above doesn't match the ID of the queue in
    # AWS Config, so we must hack our own.
    queue_url_manual = (
        f"https://sqs.{region}.amazonaws.com/{account_id}/{resource_name}"
    )
    result["config_timeline_url"] = await get_aws_config_history_url_for_resource(
        account_id,
        queue_url_manual,
        resource_name,
        "AWS::SQS::Queue",
        region=region,
    )
    return result


async def get_bucket_location_with_fallback(
    bucket_name: str, account_id: str, fallback_region: str = config.region
) -> str:
    try:
        bucket_location_res = await sync_to_async(get_bucket_location)(
            Bucket=bucket_name,
            account_number=account_id,
            assume_role=config.get("policies.role_name"),
            region=config.region,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=config.get(
                    "aws.sts_endpoint_url", "https://sts.{region}.amazonaws.com"
                ).format(region=config.region),
            ),
            client_kwargs=config.get("boto3.client_kwargs", {}),
            retry_max_attempts=2,
        )
        bucket_location = bucket_location_res.get("LocationConstraint", fallback_region)
        if not bucket_location:
            # API get_bucket_location returns None for buckets in us-east-1
            bucket_location = "us-east-1"
        if bucket_location == "EU":
            bucket_location = "eu-west-1"
        if bucket_location == "US":
            bucket_location = "us-east-1"
    except ClientError:
        bucket_location = fallback_region
        sentry_sdk.capture_exception()
    return bucket_location


async def fetch_s3_bucket(account_id: str, bucket_name: str) -> dict:
    """Fetch S3 Bucket and applicable policies

    :param account_id:
    :param bucket_name:
    :return:
    """

    from consoleme.lib.policies import get_aws_config_history_url_for_resource

    log_data: Dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "bucket_name": bucket_name,
        "account_id": account_id,
    }
    log.debug(log_data)
    created_time = None
    bucket_location = "us-east-1"

    try:
        bucket_resource = await sync_to_async(get_bucket_resource)(
            bucket_name,
            account_number=account_id,
            assume_role=config.get("policies.role_name"),
            region=config.region,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=config.get(
                    "aws.sts_endpoint_url", "https://sts.{region}.amazonaws.com"
                ).format(region=config.region),
            ),
            client_kwargs=config.get("boto3.client_kwargs", {}),
            retry_max_attempts=2,
        )
        created_time_stamp = bucket_resource.creation_date
        if created_time_stamp:
            created_time = created_time_stamp.isoformat()
    except ClientError:
        sentry_sdk.capture_exception()
    try:
        bucket_location = await get_bucket_location_with_fallback(
            bucket_name, account_id
        )
        policy: Dict = await sync_to_async(get_bucket_policy)(
            account_number=account_id,
            assume_role=config.get("policies.role_name"),
            region=bucket_location,
            Bucket=bucket_name,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=config.get(
                    "aws.sts_endpoint_url", "https://sts.{region}.amazonaws.com"
                ).format(region=config.region),
            ),
            client_kwargs=config.get("boto3.client_kwargs", {}),
            retry_max_attempts=2,
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
            region=bucket_location,
            Bucket=bucket_name,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=config.get(
                    "aws.sts_endpoint_url", "https://sts.{region}.amazonaws.com"
                ).format(region=config.region),
            ),
            client_kwargs=config.get("boto3.client_kwargs", {}),
            retry_max_attempts=2,
        )
    except ClientError as e:
        if "NoSuchTagSet" in str(e):
            tags = {"TagSet": []}
        else:
            raise

    result: Dict = {**policy, **tags, "created_time": created_time}
    result["config_timeline_url"] = await get_aws_config_history_url_for_resource(
        account_id,
        bucket_name,
        bucket_name,
        "AWS::S3::Bucket",
        region=bucket_location,
    )
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
        retry_max_attempts=2,
        client_kwargs=config.get("boto3.client_kwargs", {}),
    )

    client.attach_role_policy(RoleName=role.get("RoleName"), PolicyArn=policy_arn)
    log_data["message"] = "Applied managed policy to role"
    log.debug(log_data)
    stats.count(
        f"{function}.attach_role_policy",
        tags={"role": role.get("Arn"), "policy": policy_arn},
    )
    return True


async def delete_iam_user(account_id, iam_user_name, username) -> bool:
    """
    This function assumes the user has already been pre-authorized to delete an IAM user. it will detach all managed
    policies, delete all inline policies, delete all access keys, and finally delete the IAM user.

    :param account_id: Account ID that the IAM user is on
    :param iam_user_name: name of IAM user to delete
    :param username: actor's username
    :return:
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Attempting to delete role",
        "account_id": account_id,
        "iam_user_name": iam_user_name,
        "user": username,
    }
    log.info(log_data)
    iam_user = await fetch_iam_user_details(account_id, iam_user_name)

    # Detach managed policies
    for policy in await sync_to_async(iam_user.attached_policies.all)():
        await sync_to_async(policy.load)()
        log.info(
            {
                **log_data,
                "message": "Detaching managed policy from user",
                "policy_arn": policy.arn,
            }
        )
        await sync_to_async(policy.detach_user)(UserName=iam_user)

    # Delete Inline policies
    for policy in await sync_to_async(iam_user.policies.all)():
        await sync_to_async(policy.load)()
        log.info(
            {
                **log_data,
                "message": "Deleting inline policy on user",
                "policy_name": policy.name,
            }
        )
        await sync_to_async(policy.delete)()

    log.info({**log_data, "message": "Performing access key deletion"})
    access_keys = iam_user.access_keys.all()
    for access_key in access_keys:
        access_key.delete()

    log.info({**log_data, "message": "Performing user deletion"})
    await sync_to_async(iam_user.delete)()
    stats.count(
        f"{log_data['function']}.success", tags={"iam_user_name": iam_user_name}
    )
    return True


async def delete_iam_role(account_id, role_name, username) -> bool:
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Attempting to delete role",
        "account_id": account_id,
        "role_name": role_name,
        "user": username,
    }
    log.info(log_data)
    role = await fetch_role_details(account_id, role_name)

    for instance_profile in await sync_to_async(role.instance_profiles.all)():
        await sync_to_async(instance_profile.load)()
        log.info(
            {
                **log_data,
                "message": "Removing and deleting instance profile from role",
                "instance_profile": instance_profile.name,
            }
        )
        await sync_to_async(instance_profile.remove_role)(RoleName=role.name)
        await sync_to_async(instance_profile.delete)()

    # Detach managed policies
    for policy in await sync_to_async(role.attached_policies.all)():
        await sync_to_async(policy.load)()
        log.info(
            {
                **log_data,
                "message": "Detaching managed policy from role",
                "policy_arn": policy.arn,
            }
        )
        await sync_to_async(policy.detach_role)(RoleName=role_name)

    # Delete Inline policies
    for policy in await sync_to_async(role.policies.all)():
        await sync_to_async(policy.load)()
        log.info(
            {
                **log_data,
                "message": "Deleting inline policy on role",
                "policy_name": policy.name,
            }
        )
        await sync_to_async(policy.delete)()

    log.info({**log_data, "message": "Performing role deletion"})
    await sync_to_async(role.delete)()
    stats.count(f"{log_data['function']}.success", tags={"role_name": role_name})


async def fetch_role_details(account_id, role_name):
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Attempting to fetch role details",
        "account": account_id,
        "role": role_name,
    }
    log.info(log_data)
    iam_resource = await sync_to_async(boto3_cached_conn)(
        "iam",
        service_type="resource",
        account_number=account_id,
        region=config.region,
        assume_role=config.get("policies.role_name"),
        session_name="fetch_role_details",
        retry_max_attempts=2,
        client_kwargs=config.get("boto3.client_kwargs", {}),
    )
    try:
        iam_role = await sync_to_async(iam_resource.Role)(role_name)
    except ClientError as ce:
        if ce.response["Error"]["Code"] == "NoSuchEntity":
            log_data["message"] = "Requested role doesn't exist"
            log.error(log_data)
        raise
    await sync_to_async(iam_role.load)()
    return iam_role


async def fetch_iam_user_details(account_id, iam_user_name):
    """
    Fetches details about an IAM user from AWS. If `policies.role_name` configuration
    is set, the hub (central) account ConsoleMeInstanceProfile role will assume the
    configured role to perform the action.

    :param account_id: account ID
    :param iam_user_name: IAM user name
    :return: iam_user resource
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Attempting to fetch role details",
        "account": account_id,
        "iam_user_name": iam_user_name,
    }
    log.info(log_data)
    iam_resource = await sync_to_async(boto3_cached_conn)(
        "iam",
        service_type="resource",
        account_number=account_id,
        region=config.region,
        assume_role=config.get("policies.role_name"),
        session_name="fetch_iam_user_details",
        retry_max_attempts=2,
        client_kwargs=config.get("boto3.client_kwargs", {}),
    )
    try:
        iam_user = await sync_to_async(iam_resource.User)(iam_user_name)
    except ClientError as ce:
        if ce.response["Error"]["Code"] == "NoSuchEntity":
            log_data["message"] = "Requested user doesn't exist"
            log.error(log_data)
        raise
    await sync_to_async(iam_user.load)()
    return iam_user


async def create_iam_role(create_model: RoleCreationRequestModel, username):
    """
    Creates IAM role.
    :param create_model: RoleCreationRequestModel, which has the following attributes:
        account_id: destination account's ID
        role_name: destination role name
        description: optional string - description of the role
                     default: Role created by {username} through ConsoleMe
        instance_profile: optional boolean - whether to create an instance profile and attach it to the role or not
                     default: True
    :param username: username of user requesting action
    :return: results: - indicating the results of each action
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Attempting to create role",
        "account_id": create_model.account_id,
        "role_name": create_model.role_name,
        "user": username,
    }
    log.info(log_data)

    default_trust_policy = config.get(
        "user_role_creator.default_trust_policy",
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        },
    )
    if default_trust_policy is None:
        raise MissingConfigurationValue(
            "Missing Default Assume Role Policy Configuration"
        )

    default_max_session_duration = config.get(
        "user_role_creator.default_max_session_duration", 3600
    )

    if create_model.description:
        description = create_model.description
    else:
        description = f"Role created by {username} through ConsoleMe"

    iam_client = await sync_to_async(boto3_cached_conn)(
        "iam",
        service_type="client",
        account_number=create_model.account_id,
        region=config.region,
        assume_role=config.get("policies.role_name"),
        session_name=sanitize_session_name("create_role_" + username),
        retry_max_attempts=2,
        client_kwargs=config.get("boto3.client_kwargs", {}),
    )
    results = {"errors": 0, "role_created": "false", "action_results": []}
    try:
        await sync_to_async(iam_client.create_role)(
            RoleName=create_model.role_name,
            AssumeRolePolicyDocument=json.dumps(default_trust_policy),
            Description=description,
            MaxSessionDuration=default_max_session_duration,
            Tags=[],
        )
        results["action_results"].append(
            {
                "status": "success",
                "message": f"Role arn:aws:iam::{create_model.account_id}:role/{create_model.role_name} "
                f"successfully created",
            }
        )
        results["role_created"] = "true"
    except Exception as e:
        log_data["message"] = "Exception occurred creating role"
        log_data["error"] = str(e)
        log.error(log_data, exc_info=True)
        results["action_results"].append(
            {
                "status": "error",
                "message": f"Error creating role {create_model.role_name} in account {create_model.account_id}:"
                + str(e),
            }
        )
        results["errors"] += 1
        sentry_sdk.capture_exception()
        # Since we were unable to create the role, no point continuing, just return
        return results

    # If here, role has been successfully created, add status updates for each action
    results["action_results"].append(
        {
            "status": "success",
            "message": "Successfully added default Assume Role Policy Document",
        }
    )
    results["action_results"].append(
        {
            "status": "success",
            "message": "Successfully added description: " + description,
        }
    )

    # Create instance profile and attach if specified
    if create_model.instance_profile:
        try:
            await sync_to_async(iam_client.create_instance_profile)(
                InstanceProfileName=create_model.role_name
            )
            await sync_to_async(iam_client.add_role_to_instance_profile)(
                InstanceProfileName=create_model.role_name,
                RoleName=create_model.role_name,
            )
            results["action_results"].append(
                {
                    "status": "success",
                    "message": f"Successfully added instance profile {create_model.role_name} to role "
                    f"{create_model.role_name}",
                }
            )
        except Exception as e:
            log_data[
                "message"
            ] = "Exception occurred creating/attaching instance profile"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            sentry_sdk.capture_exception()
            results["action_results"].append(
                {
                    "status": "error",
                    "message": f"Error creating/attaching instance profile {create_model.role_name} to role: "
                    + str(e),
                }
            )
            results["errors"] += 1

    stats.count(
        f"{log_data['function']}.success", tags={"role_name": create_model.role_name}
    )
    log_data["message"] = "Successfully created role"
    log.info(log_data)
    # Force caching of role
    try:
        aws = get_plugin_by_name(config.get("plugins.aws", "default_aws"))()
        role_arn = (
            f"arn:aws:iam::{create_model.account_id}:role/{create_model.role_name}"
        )
        await aws.fetch_iam_role(create_model.account_id, role_arn, force_refresh=True)
    except Exception as e:
        log.error({**log_data, "message": "Unable to cache role", "error": str(e)})
        sentry_sdk.capture_exception()
    return results


async def clone_iam_role(clone_model: CloneRoleRequestModel, username):
    """
    Clones IAM role within same account or across account, always creating and attaching instance profile if one exists
    on the source role.
    ;param username: username of user requesting action
    ;:param clone_model: CloneRoleRequestModel, which has the following attributes:
        account_id: source role's account ID
        role_name: source role's name
        dest_account_id: destination role's account ID (may be same as account_id)
        dest_role_name: destination role's name
        clone_options: dict to indicate what to copy when cloning:
            assume_role_policy: bool
                default: False - uses default ConsoleMe AssumeRolePolicy
            tags: bool
                default: False - defaults to no tags
            copy_description: bool
                default: False - defaults to copying provided description or default description
            description: string
                default: "Role cloned via ConsoleMe by `username` from `arn:aws:iam::<account_id>:role/<role_name>`
                if copy_description is True, then description is ignored
            inline_policies: bool
                default: False - defaults to no inline policies
            managed_policies: bool
                default: False - defaults to no managed policies
    :return: results: - indicating the results of each action
    """

    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Attempting to clone role",
        "account_id": clone_model.account_id,
        "role_name": clone_model.role_name,
        "dest_account_id": clone_model.dest_account_id,
        "dest_role_name": clone_model.dest_role_name,
        "user": username,
    }
    log.info(log_data)
    role = await fetch_role_details(clone_model.account_id, clone_model.role_name)

    default_trust_policy = config.get("user_role_creator.default_trust_policy")
    trust_policy = (
        role.assume_role_policy_document
        if clone_model.options.assume_role_policy
        else default_trust_policy
    )
    if trust_policy is None:
        raise MissingConfigurationValue(
            "Missing Default Assume Role Policy Configuration"
        )

    default_max_session_duration = config.get(
        "user_role_creator.default_max_session_duration", 3600
    )

    max_session_duration = (
        role.max_session_duration
        if clone_model.options.max_session_duration
        else default_max_session_duration
    )

    if (
        clone_model.options.copy_description
        and role.description is not None
        and role.description != ""
    ):
        description = role.description
    elif (
        clone_model.options.description is not None
        and clone_model.options.description != ""
    ):
        description = clone_model.options.description
    else:
        description = f"Role cloned via ConsoleMe by {username} from {role.arn}"

    tags = role.tags if clone_model.options.tags and role.tags else []

    iam_client = await sync_to_async(boto3_cached_conn)(
        "iam",
        service_type="client",
        account_number=clone_model.dest_account_id,
        region=config.region,
        assume_role=config.get("policies.role_name"),
        session_name=sanitize_session_name("clone_role_" + username),
        retry_max_attempts=2,
        client_kwargs=config.get("boto3.client_kwargs", {}),
    )
    results = {"errors": 0, "role_created": "false", "action_results": []}
    try:
        await sync_to_async(iam_client.create_role)(
            RoleName=clone_model.dest_role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=description,
            MaxSessionDuration=max_session_duration,
            Tags=tags,
        )
        results["action_results"].append(
            {
                "status": "success",
                "message": f"Role arn:aws:iam::{clone_model.dest_account_id}:role/{clone_model.dest_role_name} "
                f"successfully created",
            }
        )
        results["role_created"] = "true"
    except Exception as e:
        log_data["message"] = "Exception occurred creating cloned role"
        log_data["error"] = str(e)
        log.error(log_data, exc_info=True)
        results["action_results"].append(
            {
                "status": "error",
                "message": f"Error creating role {clone_model.dest_role_name} in account {clone_model.dest_account_id}:"
                + str(e),
            }
        )
        results["errors"] += 1
        sentry_sdk.capture_exception()
        # Since we were unable to create the role, no point continuing, just return
        return results

    if clone_model.options.tags:
        results["action_results"].append(
            {"status": "success", "message": "Successfully copied tags"}
        )
    if clone_model.options.assume_role_policy:
        results["action_results"].append(
            {
                "status": "success",
                "message": "Successfully copied Assume Role Policy Document",
            }
        )
    else:
        results["action_results"].append(
            {
                "status": "success",
                "message": "Successfully added default Assume Role Policy Document",
            }
        )
    if (
        clone_model.options.copy_description
        and role.description is not None
        and role.description != ""
    ):
        results["action_results"].append(
            {"status": "success", "message": "Successfully copied description"}
        )
    elif clone_model.options.copy_description:
        results["action_results"].append(
            {
                "status": "error",
                "message": "Failed to copy description, so added default description: "
                + description,
            }
        )
    else:
        results["action_results"].append(
            {
                "status": "success",
                "message": "Successfully added description: " + description,
            }
        )
    # Create instance profile and attach if it exists in source role
    if len(list(await sync_to_async(role.instance_profiles.all)())) > 0:
        try:
            await sync_to_async(iam_client.create_instance_profile)(
                InstanceProfileName=clone_model.dest_role_name
            )
            await sync_to_async(iam_client.add_role_to_instance_profile)(
                InstanceProfileName=clone_model.dest_role_name,
                RoleName=clone_model.dest_role_name,
            )
            results["action_results"].append(
                {
                    "status": "success",
                    "message": f"Successfully added instance profile {clone_model.dest_role_name} to role "
                    f"{clone_model.dest_role_name}",
                }
            )
        except Exception as e:
            log_data[
                "message"
            ] = "Exception occurred creating/attaching instance profile"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            sentry_sdk.capture_exception()
            results["action_results"].append(
                {
                    "status": "error",
                    "message": f"Error creating/attaching instance profile {clone_model.dest_role_name} to role: "
                    + str(e),
                }
            )
            results["errors"] += 1

    # other optional attributes to copy over after role has been successfully created

    cloned_role = await fetch_role_details(
        clone_model.dest_account_id, clone_model.dest_role_name
    )

    # Copy inline policies
    if clone_model.options.inline_policies:
        for src_policy in await sync_to_async(role.policies.all)():
            await sync_to_async(src_policy.load)()
            try:
                dest_policy = await sync_to_async(cloned_role.Policy)(src_policy.name)
                await sync_to_async(dest_policy.put)(
                    PolicyDocument=json.dumps(src_policy.policy_document)
                )
                results["action_results"].append(
                    {
                        "status": "success",
                        "message": f"Successfully copied inline policy {src_policy.name}",
                    }
                )
            except Exception as e:
                log_data["message"] = "Exception occurred copying inline policy"
                log_data["error"] = str(e)
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()
                results["action_results"].append(
                    {
                        "status": "error",
                        "message": f"Error copying inline policy {src_policy.name}: "
                        + str(e),
                    }
                )
                results["errors"] += 1

    # Copy managed policies
    if clone_model.options.managed_policies:
        for src_policy in await sync_to_async(role.attached_policies.all)():
            await sync_to_async(src_policy.load)()
            dest_policy_arn = src_policy.arn.replace(
                clone_model.account_id, clone_model.dest_account_id
            )
            try:
                await sync_to_async(cloned_role.attach_policy)(
                    PolicyArn=dest_policy_arn
                )
                results["action_results"].append(
                    {
                        "status": "success",
                        "message": f"Successfully attached managed policy {src_policy.arn} as {dest_policy_arn}",
                    }
                )
            except Exception as e:
                log_data["message"] = "Exception occurred copying managed policy"
                log_data["error"] = str(e)
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()
                results["action_results"].append(
                    {
                        "status": "error",
                        "message": f"Error attaching managed policy {dest_policy_arn}: "
                        + str(e),
                    }
                )
                results["errors"] += 1

    stats.count(
        f"{log_data['function']}.success", tags={"role_name": clone_model.role_name}
    )
    log_data["message"] = "Successfully cloned role"
    log.info(log_data)
    return results


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
    if isinstance(role.get("CreateDate"), str):
        role["CreateDate"] = parse(role.get("CreateDate"))
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


def get_region_from_arn(arn):
    """Given an ARN, return the region in the ARN, if it is available. In certain cases like S3 it is not"""
    result = parse_arn(arn)
    # Support S3 buckets with no values under region
    if result["region"] is None:
        result = ""
    else:
        result = result["region"]
    return result


def get_resource_from_arn(arn):
    """Given an ARN, parse it according to ARN namespacing and return the resource. See
    http://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html for more details on ARN namespacing.
    """
    result = parse_arn(arn)
    return result["resource"]


def get_service_from_arn(arn):
    """Given an ARN string, return the service"""
    result = parse_arn(arn)
    return result["service"]


async def get_enabled_regions_for_account(account_id: str) -> Set[str]:
    """
    Returns a list of regions enabled for an account based on an EC2 Describe Regions call. Can be overridden with a
    global configuration of static regions (Configuration key: `celery.sync_regions`), or a configuration of specific
    regions per account (Configuration key:  `get_enabled_regions_for_account.{account_id}`)
    """
    enabled_regions_for_account = config.get(
        f"get_enabled_regions_for_account.{account_id}"
    )
    if enabled_regions_for_account:
        return enabled_regions_for_account

    celery_sync_regions = config.get("celery.sync_regions", [])
    if celery_sync_regions:
        return celery_sync_regions

    client = await sync_to_async(boto3_cached_conn)(
        "ec2",
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        read_only=True,
        retry_max_attempts=2,
        client_kwargs=config.get("boto3.client_kwargs", {}),
    )

    regions = await sync_to_async(client.describe_regions)()
    return {r["RegionName"] for r in regions["Regions"]}


async def access_analyzer_validate_policy(
    policy: str, log_data, policy_type: str = "IDENTITY_POLICY"
) -> List[Dict[str, Any]]:
    try:
        enhanced_findings = []
        client = await sync_to_async(boto3.client)(
            "accessanalyzer",
            region_name=config.region,
            **config.get("boto3.client_kwargs", {}),
        )
        access_analyzer_response = await sync_to_async(client.validate_policy)(
            policyDocument=policy,
            policyType=policy_type,  # ConsoleMe only supports identity policy analysis currently
        )
        for finding in access_analyzer_response.get("findings", []):
            for location in finding.get("locations", []):
                enhanced_findings.append(
                    {
                        "issue": finding.get("issueCode"),
                        "detail": "",
                        "location": {
                            "line": location.get("span", {})
                            .get("start", {})
                            .get("line"),
                            "column": location.get("span", {})
                            .get("start", {})
                            .get("column"),
                            "filepath": None,
                        },
                        "severity": finding.get("findingType"),
                        "title": finding.get("issueCode"),
                        "description": finding.get("findingDetails"),
                    }
                )
        return enhanced_findings
    except (ParamValidationError, ClientError) as e:
        log.error(
            {
                **log_data,
                "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                "message": "Error retrieving Access Analyzer data",
                "policy": policy,
                "error": str(e),
            }
        )
        sentry_sdk.capture_exception()
        return []


async def parliament_validate_iam_policy(policy: str) -> List[Dict[str, Any]]:
    analyzed_policy = await sync_to_async(analyze_policy_string)(policy)
    findings = analyzed_policy.findings

    enhanced_findings = []

    for finding in findings:
        enhanced_finding = await sync_to_async(enhance_finding)(finding)
        enhanced_findings.append(
            {
                "issue": enhanced_finding.issue,
                "detail": json.dumps(enhanced_finding.detail),
                "location": enhanced_finding.location,
                "severity": enhanced_finding.severity,
                "title": enhanced_finding.title,
                "description": enhanced_finding.description,
            }
        )
    return enhanced_findings


async def validate_iam_policy(policy: str, log_data: Dict):
    parliament_findings: List = await parliament_validate_iam_policy(policy)
    access_analyzer_findings: List = await access_analyzer_validate_policy(
        policy, log_data, policy_type="IDENTITY_POLICY"
    )
    return parliament_findings + access_analyzer_findings


async def get_all_scps(force_sync=False) -> Dict[str, List[ServiceControlPolicyModel]]:
    """Retrieve a dictionary containing all Service Control Policies across organizations

    Args:
        force_sync: force a cache update
    """
    redis_key = config.get(
        "cache_scps_across_organizations.redis.key.all_scps_key", "ALL_AWS_SCPS"
    )
    scps = await retrieve_json_data_from_redis_or_s3(
        redis_key,
        s3_bucket=config.get("cache_scps_across_organizations.s3.bucket"),
        s3_key=config.get(
            "cache_scps_across_organizations.s3.file", "scps/cache_scps_v1.json.gz"
        ),
        default={},
        max_age=86400,
    )
    if force_sync or not scps:
        scps = await cache_all_scps()
    scp_models = {}
    for account, org_scps in scps.items():
        scp_models[account] = [ServiceControlPolicyModel(**scp) for scp in org_scps]
    return scp_models


async def cache_all_scps() -> Dict[str, Any]:
    """Store a dictionary of all Service Control Policies across organizations in the cache"""
    all_scps = {}
    for organization in config.get("cache_accounts_from_aws_organizations", []):
        org_account_id = organization.get("organizations_master_account_id")
        role_to_assume = organization.get(
            "organizations_master_role_to_assume", config.get("policies.role_name")
        )
        if not org_account_id:
            raise MissingConfigurationValue(
                "Your AWS Organizations Master Account ID is not specified in configuration. "
                "Unable to sync accounts from "
                "AWS Organizations"
            )

        if not role_to_assume:
            raise MissingConfigurationValue(
                "ConsoleMe doesn't know what role to assume to retrieve account information "
                "from AWS Organizations. please set the appropriate configuration value."
            )
        org_scps = await retrieve_scps_for_organization(
            org_account_id, role_to_assume=role_to_assume, region=config.region
        )
        all_scps[org_account_id] = org_scps
    redis_key = config.get(
        "cache_scps_across_organizations.redis.key.all_scps_key", "ALL_AWS_SCPS"
    )
    s3_bucket = None
    s3_key = None
    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev", "test"]:
        s3_bucket = config.get("cache_scps_across_organizations.s3.bucket")
        s3_key = config.get(
            "cache_scps_across_organizations.s3.file", "scps/cache_scps_v1.json.gz"
        )
    await store_json_results_in_redis_and_s3(
        all_scps,
        redis_key=redis_key,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
    )
    return all_scps


async def get_org_structure(force_sync=False) -> Dict[str, Any]:
    """Retrieve a dictionary containing the organization structure

    Args:
        force_sync: force a cache update
    """
    redis_key = config.get(
        "cache_organization_structure.redis.key.org_structure_key", "AWS_ORG_STRUCTURE"
    )
    org_structure = await retrieve_json_data_from_redis_or_s3(
        redis_key,
        s3_bucket=config.get("cache_organization_structure.s3.bucket"),
        s3_key=config.get(
            "cache_organization_structure.s3.file",
            "scps/cache_org_structure_v1.json.gz",
        ),
        default={},
    )
    if force_sync or not org_structure:
        org_structure = await cache_org_structure()
    return org_structure


async def cache_org_structure() -> Dict[str, Any]:
    """Store a dictionary of the organization structure in the cache"""
    all_org_structure = {}
    for organization in config.get("cache_accounts_from_aws_organizations", []):
        org_account_id = organization.get("organizations_master_account_id")
        role_to_assume = organization.get(
            "organizations_master_role_to_assume", config.get("policies.role_name")
        )
        if not org_account_id:
            raise MissingConfigurationValue(
                "Your AWS Organizations Master Account ID is not specified in configuration. "
                "Unable to sync accounts from "
                "AWS Organizations"
            )

        if not role_to_assume:
            raise MissingConfigurationValue(
                "ConsoleMe doesn't know what role to assume to retrieve account information "
                "from AWS Organizations. please set the appropriate configuration value."
            )
        org_structure = await retrieve_org_structure(
            org_account_id, region=config.region
        )
        all_org_structure.update(org_structure)
    redis_key = config.get(
        "cache_organization_structure.redis.key.org_structure_key", "AWS_ORG_STRUCTURE"
    )
    s3_bucket = None
    s3_key = None
    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev", "test"]:
        s3_bucket = config.get("cache_organization_structure.s3.bucket")
        s3_key = config.get(
            "cache_organization_structure.s3.file",
            "scps/cache_org_structure_v1.json.gz",
        )
    await store_json_results_in_redis_and_s3(
        all_org_structure,
        redis_key=redis_key,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
    )
    return all_org_structure


async def _is_member_of_ou(
    identifier: str, ou: Dict[str, Any]
) -> Tuple[bool, Set[str]]:
    """Recursively walk org structure to determine if the account or OU is in the org and, if so, return all OUs of which the account or OU is a member

    Args:
        identifier: AWS account or OU ID
        ou: dictionary representing the organization/organizational unit structure to search
    """
    found = False
    ou_path = set()
    for child in ou.get("Children", []):
        if child.get("Id") == identifier:
            found = True
        elif child.get("Type") == "ORGANIZATIONAL_UNIT":
            found, ou_path = await _is_member_of_ou(identifier, child)
        if found:
            ou_path.add(ou.get("Id"))
            break
    return found, ou_path


async def get_organizational_units_for_account(identifier: str) -> Set[str]:
    """Return a set of Organizational Unit IDs for a given account or OU ID

    Args:
        identifier: AWS account or OU ID
    """
    all_orgs = await get_org_structure()
    organizational_units = set()
    for org_id, org_structure in all_orgs.items():
        found, organizational_units = await _is_member_of_ou(identifier, org_structure)
        if found:
            break
    if not organizational_units:
        log.warning("could not find account in organization")
    return organizational_units


async def _scp_targets_account_or_ou(
    scp: ServiceControlPolicyModel, identifier: str, organizational_units: Set[str]
) -> bool:
    """Return True if the provided SCP targets the account or OU identifier provided

    Args:
        scp: Service Control Policy whose targets we check
        identifier: AWS account or OU ID
        organizational_units: set of IDs for OUs of which the identifier is a member
    """
    for target in scp.targets:
        if target.target_id == identifier or target.target_id in organizational_units:
            return True
    return False


async def get_scps_for_account_or_ou(identifier: str) -> ServiceControlPolicyArrayModel:
    """Retrieve a list of Service Control Policies for the account or OU specified by the identifier

    Args:
        identifier: AWS account or OU ID
    """
    all_scps = await get_all_scps()
    account_ous = await get_organizational_units_for_account(identifier)
    scps_for_account = []
    for org_account_id, scps in all_scps.items():
        # Iterate through each org's SCPs and see if the provided account_id is in the targets
        for scp in scps:
            if await _scp_targets_account_or_ou(scp, identifier, account_ous):
                scps_for_account.append(scp)
    scps = ServiceControlPolicyArrayModel(__root__=scps_for_account)
    return scps


async def minimize_iam_policy_statements(
    inline_iam_policy_statements: List[Dict], disregard_sid=True
) -> List[Dict]:
    """
    Minimizes a list of inline IAM policy statements.

    1. Policies that are identical except for the resources will have the resources merged into a single statement
    with the same actions, effects, conditions, etc.

    2. Policies that have an identical resource, but different actions, will be combined if the rest of the policy
    is identical.
    :param inline_iam_policy_statements: A list of IAM policy statement dictionaries
    :return: A potentially more compact list of IAM policy statement dictionaries
    """
    exclude_ids = []
    minimized_statements = []

    inline_iam_policy_statements = await normalize_policies(
        inline_iam_policy_statements
    )

    for i in range(len(inline_iam_policy_statements)):
        inline_iam_policy_statement = inline_iam_policy_statements[i]
        if disregard_sid:
            inline_iam_policy_statement.pop("Sid", None)
        if i in exclude_ids:
            # We've already combined this policy with another. Ignore it.
            continue
        for j in range(i + 1, len(inline_iam_policy_statements)):
            if j in exclude_ids:
                # We've already combined this policy with another. Ignore it.
                continue
            inline_iam_policy_statement_to_compare = inline_iam_policy_statements[j]
            if disregard_sid:
                inline_iam_policy_statement_to_compare.pop("Sid", None)
            # Check to see if policy statements are identical except for a given element. Merge the policies
            # if possible.
            for element in [
                "Resource",
                "Action",
                "NotAction",
                "NotResource",
                "NotPrincipal",
            ]:
                if not (
                    inline_iam_policy_statement.get(element)
                    or inline_iam_policy_statement_to_compare.get(element)
                ):
                    # This function won't handle `Condition`.
                    continue
                diff = DeepDiff(
                    inline_iam_policy_statement,
                    inline_iam_policy_statement_to_compare,
                    ignore_order=True,
                    exclude_paths=[f"root['{element}']"],
                )
                if not diff:
                    exclude_ids.append(j)
                    # Policy can be minimized
                    inline_iam_policy_statement[element] = sorted(
                        list(
                            set(
                                inline_iam_policy_statement[element]
                                + inline_iam_policy_statement_to_compare[element]
                            )
                        )
                    )
                    break

    for i in range(len(inline_iam_policy_statements)):
        if i not in exclude_ids:
            inline_iam_policy_statements[i] = sort_dict(inline_iam_policy_statements[i])
            minimized_statements.append(inline_iam_policy_statements[i])
    # TODO(cccastrapel): Intelligently combine actions and/or resources if they include wildcards
    minimized_statements = await normalize_policies(minimized_statements)
    return minimized_statements


async def normalize_policies(policies: List[Any]) -> List[Any]:
    """
    Normalizes policy statements to ensure appropriate AWS policy elements are lists (such as actions and resources),
    lowercase, and sorted. It will remove duplicate entries and entries that are superseded by other elements.
    """

    for policy in policies:
        for element in [
            "Resource",
            "Action",
            "NotAction",
            "NotResource",
            "NotPrincipal",
        ]:
            if not policy.get(element):
                continue
            if isinstance(policy.get(element), str):
                policy[element] = [policy[element]]
            # Policy elements can be lowercased, except for resources. Some resources
            # (such as IAM roles) are case sensitive
            if element in ["Resource", "NotResource", "NotPrincipal"]:
                policy[element] = list(set(policy[element]))
            else:
                policy[element] = list(set([x.lower() for x in policy[element]]))
            modified_elements = set()
            for i in range(len(policy[element])):
                matched = False
                # Sorry for the magic. this is iterating through all elements of a list that aren't the current element
                for compare_value in policy[element][:i] + policy[element][(i + 1) :]:
                    if fnmatch.fnmatch(policy[element][i], compare_value):
                        matched = True
                        break
                if not matched:
                    modified_elements.add(policy[element][i])
            policy[element] = sorted(modified_elements)
    return policies


def allowed_to_sync_role(
    role_arn: str, role_tags: List[Optional[Dict[str, str]]]
) -> bool:
    """
    This function determines whether ConsoleMe is allowed to sync or otherwise manipulate an IAM role. By default,
    ConsoleMe will sync all roles that it can get its grubby little hands on. However, ConsoleMe administrators can tell
    ConsoleMe to only sync roles with either 1) Specific ARNs, or 2) Specific tag key/value pairs. All configured tags
    must exist on the role for ConsoleMe to sync it., or 3) Specific tag keys

    Here's an example configuration for a tag-based restriction:

    ```
    roles:
      allowed_tags:
        tag1: value1
        tag2: value2
    ```

    And another one for an ARN-based restriction:

    ```
    roles:
      allowed_arns:
        - arn:aws:iam::111111111111:role/role-name-here-1
        - arn:aws:iam::111111111111:role/role-name-here-2
        - arn:aws:iam::111111111111:role/role-name-here-3
        - arn:aws:iam::222222222222:role/role-name-here-1
        - arn:aws:iam::333333333333:role/role-name-here-1
    ```

    And another one for an tag key based restriction:

    ```
    roles:
      allowed_tag_keys:
        - cosoleme-authorized
        - consoleme-authorized-cli-only
    ```

    :param
        arn: The AWS role arn
        role_tags: A dictionary of role tags

    :return: boolean specifying whether ConsoleMe is allowed to sync / access the role
    """
    allowed_tags = config.get("roles.allowed_tags", {})
    allowed_arns = config.get("roles.allowed_arns", [])
    allowed_tag_keys = config.get("roles.allowed_tag_keys", [])
    if not allowed_tags and not allowed_arns and not allowed_tag_keys:
        return True

    if role_arn in allowed_arns:
        return True

    # Convert list of role tag dicts to an array of tag keys
    # ex:
    # role_tags = [{'Key': 'consoleme-authorized', 'Value': 'consoleme_admins'},
    # {'Key': 'Description', 'Value': 'ConsoleMe OSS Demo Role'}]
    # so: actual_tag_keys = ['consoleme-authorized', 'Description']
    actual_tag_keys = [d["Key"] for d in role_tags]

    # If any allowed tag key exists in the role's actual_tags this condition will pass
    if allowed_tag_keys and any(x in allowed_tag_keys for x in actual_tag_keys):
        return True

    # Convert list of role tag dicts to a single key/value dict of tags
    # ex:
    # role_tags = [{'Key': 'consoleme-authorized', 'Value': 'consoleme_admins'},
    # {'Key': 'Description', 'Value': 'ConsoleMe OSS Demo Role'}]
    # so: actual_tags = {'consoleme-authorized': 'consoleme_admins', 'Description': 'ConsoleMe OSS Demo Role'}
    actual_tags = {
        d["Key"]: d["Value"] for d in role_tags
    }  # Convert List[Dicts] to 1 Dict

    # All configured allowed_tags must exist in the role's actual_tags for this condition to pass
    if allowed_tags and allowed_tags.items() <= actual_tags.items():
        return True
    return False


def remove_temp_policies(role, iam_client) -> bool:
    """
    If this feature is enabled, it will look at inline role policies and remove expired policies if they have been
    designated as temporary. Policies can be designated as temporary through a certain prefix in the policy name.
    In the future, we may allow specifying temporary policies by `Sid` or other means.

    :param role: A single AWS IAM role entry in dictionary format as returned by the `get_account_authorization_details`
        call
    :return: bool: Whether policies were removed or not
    """
    function = f"{__name__}.{sys._getframe().f_code.co_name}"

    if not config.get("policies.temp_policy_support"):
        return False

    temp_policy_prefix = config.get("policies.temp_policy_prefix", "cm_delete-on")
    if not temp_policy_prefix:
        return False
    current_dateint = datetime.today().strftime("%Y%m%d")

    log_data = {
        "function": function,
        "temp_policy_prefix": temp_policy_prefix,
        "role_arn": role["Arn"],
    }
    policies_removed = False
    for policy in role["RolePolicyList"]:
        try:
            policy_name = policy["PolicyName"]
            if not policy_name.startswith(temp_policy_prefix):
                continue
            expiration_date = policy_name.replace(temp_policy_prefix, "", 1).split("_")[
                1
            ]
            if not current_dateint >= expiration_date:
                continue
            log.debug(
                {
                    **log_data,
                    "message": "Deleting temporary policy",
                    "policy_name": policy_name,
                }
            )
            iam_client.delete_role_policy(
                RoleName=role["RoleName"], PolicyName=policy_name
            )
            policies_removed = True
        except Exception as e:
            log.error(
                {
                    **log_data,
                    "message": "Error deleting temporary IAM policy",
                    "error": str(e),
                },
                exc_info=True,
            )
            sentry_sdk.capture_exception()

    return policies_removed


def get_aws_principal_owner(role_details: Dict[str, Any]) -> Optional[str]:
    """
    Identifies the owning user/group of an AWS principal based on one or more trusted and configurable principal tags.
    `owner` is used to notify application owners of permission problems with their detected AWS principals or resources
    if another identifier (ie: session name) for a principal doesn't point to a specific user for notification.

    :return: owner: str
    """
    owner = None
    owner_tag_names = config.get("aws.tags.owner", [])
    if not owner_tag_names:
        return owner
    if isinstance(owner_tag_names, str):
        owner_tag_names = [owner_tag_names]
    role_tags = role_details.get("Tags")
    for owner_tag_name in owner_tag_names:
        for role_tag in role_tags:
            if role_tag["Key"] == owner_tag_name:
                return role_tag["Value"]
    return owner


async def resource_arn_known_in_aws_config(
    resource_arn: str,
    run_query: bool = True,
    run_query_with_aggregator: bool = True,
    expiration_seconds: int = config.get(
        "aws.resource_arn_known_in_aws_config.expiration_seconds", 3600
    ),
) -> bool:
    """
    Determines if the resource ARN is known in AWS Config. AWS config does not store all resource
    types, nor will it account for cross-organizational resources, so the result of this function shouldn't be used
    to determine if a resource "exists" or not.

    A more robust approach is determining the resource type and querying AWS API directly to see if it exists, but this
    requires a lot of code.

    Note: This data may be stale by ~ 1 hour and 15 minutes (local results caching + typical AWS config delay)

    :param expiration_seconds: Number of seconds to consider stored result expired
    :param resource_arn: ARN of the resource we want to look up
    :param run_query: Should we run an AWS config query if we're not able to find the resource in our AWS Config cache?
    :param run_query_with_aggregator: Should we run the AWS Config query on our AWS Config aggregator?
    :return:
    """
    known_arn = False
    if not resource_arn.startswith("arn:aws:"):
        return known_arn

    resources_from_aws_config_redis_key: str = config.get(
        "aws_config_cache.redis_key", "AWSCONFIG_RESOURCE_CACHE"
    )

    if red.exists(resources_from_aws_config_redis_key) and red.hget(
        resources_from_aws_config_redis_key, resource_arn
    ):
        return True

    resource_arn_exists_temp_matches_redis_key: str = config.get(
        "resource_arn_known_in_aws_config.redis.temp_matches_key",
        "TEMP_QUERIED_RESOURCE_ARN_CACHE",
    )

    # To prevent repetitive queries against AWS config, first see if we've already ran a query recently
    result = await redis_hgetex(
        resource_arn_exists_temp_matches_redis_key, resource_arn
    )
    if result:
        return result["known"]

    if not run_query:
        return False

    r = await sync_to_async(query)(
        f"select arn where arn = '{resource_arn}'",
        use_aggregator=run_query_with_aggregator,
    )
    if r:
        known_arn = True
    # To prevent future repetitive queries on AWS Config, set our result in Redis with an expiration
    await redis_hsetex(
        resource_arn_exists_temp_matches_redis_key,
        resource_arn,
        {"known": known_arn},
        expiration_seconds=expiration_seconds,
    )

    return known_arn


async def simulate_iam_principal_action(
    principal_arn,
    action,
    resource_arn,
    source_ip,
    expiration_seconds: int = config.get(
        "aws.simulate_iam_principal_action.expiration_seconds", 3600
    ),
):
    """
    Simulates an IAM principal action affecting a resource

    :return:
    """
    # simulating IAM principal policies is expensive.
    # Temporarily cache and return results by principal_arn, action, and resource_arn. We don't consider source_ip
    # when caching because it could vary greatly for application roles running on multiple instances/containers.
    resource_arn_exists_temp_matches_redis_key: str = config.get(
        "resource_arn_known_in_aws_config.redis.temp_matches_key",
        "TEMP_POLICY_SIMULATION_CACHE",
    )

    cache_key = f"{principal_arn}-{action}-{resource_arn}"
    result = await redis_hgetex(resource_arn_exists_temp_matches_redis_key, cache_key)
    if result:
        return result

    ip_regex = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    context_entries = []
    if source_ip and re.match(ip_regex, source_ip):
        context_entries.append(
            {
                "ContextKeyName": "aws:SourceIp",
                "ContextKeyValues": [source_ip],
                "ContextKeyType": "ip",
            }
        )
    account_id = principal_arn.split(":")[4]
    client = await sync_to_async(boto3_cached_conn)(
        "iam",
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=config.get(
                "aws.sts_endpoint_url", "https://sts.{region}.amazonaws.com"
            ).format(region=config.region),
        ),
        retry_max_attempts=2,
    )
    try:
        response = await sync_to_async(client.simulate_principal_policy)(
            PolicySourceArn=principal_arn,
            ActionNames=[
                action,
            ],
            ResourceArns=[
                resource_arn,
            ],
            # TODO: Attach resource policy when discoverable
            # ResourcePolicy='string',
            # TODO: Attach Account ID of resource
            # ResourceOwner='string',
            ContextEntries=context_entries,
            MaxItems=100,
        )

        await redis_hsetex(
            resource_arn_exists_temp_matches_redis_key,
            resource_arn,
            response["EvaluationResults"],
            expiration_seconds=expiration_seconds,
        )
    except Exception:
        sentry_sdk.capture_exception()
        return None
    return response["EvaluationResults"]


async def get_iam_principal_owner(arn: str, aws: Any) -> Optional[str]:
    principal_details = {}
    principal_type = arn.split(":")[-1].split("/")[0]
    account_id = arn.split(":")[4]
    # trying to find principal for subsequent queries
    if principal_type == "role":
        principal_details = await aws().fetch_iam_role(account_id, arn)
    elif principal_type == "user":
        principal_details = await aws().fetch_iam_user(account_id, arn)
    return principal_details.get("owner")


def sanitize_session_name(unsanitized_session_name):
    """
    This function sanitizes the session name typically passed in an assume_role call, to verify that it's
    """
    valid_characters_re = re.compile(r"[\w+=,.@-]")

    sanitized_session_name = ""
    max_length = 64  # Session names have a length limit of 64 characters
    for char in unsanitized_session_name:
        if len(sanitized_session_name) == max_length:
            break
        if valid_characters_re.match(char):
            sanitized_session_name += char
    return sanitized_session_name

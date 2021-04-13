import json
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
from consoleme.lib.cache import retrieve_json_data_from_redis_or_s3
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.redis import RedisHandler, redis_hget
from consoleme.models import CloneRoleRequestModel, RoleCreationRequestModel

ALL_IAM_MANAGED_POLICIES: dict = {}
ALL_IAM_MANAGED_POLICIES_LAST_UPDATE: int = 0

log = config.get_logger(__name__)
auth = get_plugin_by_name(config.get("plugins.auth", "default_auth"))()
stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()


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

    if ALL_IAM_MANAGED_POLICIES:
        return json.loads(ALL_IAM_MANAGED_POLICIES.get(account_id, "[]"))
    else:
        s3_bucket = config.get("account_resource_cache.s3.bucket")
        s3_key = config.get("account_resource_cache.s3.file", "").format(
            resource_type="managed_policies", account_id=account_id
        )
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
            s3_key=config.get("aws_config_cache_combined.s3.file"),
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
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
    )

    result: Dict = await sync_to_async(get_topic_attributes)(
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        TopicArn=arn,
        region=region,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
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
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
    )

    result: Dict = await sync_to_async(get_queue_attributes)(
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        region=region,
        QueueUrl=queue_url,
        AttributeNames=["All"],
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
    )

    tags: Dict = await sync_to_async(list_queue_tags)(
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        region=region,
        QueueUrl=queue_url,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
    )
    result["TagSet"]: list = []
    result["QueueUrl"]: str = queue_url
    if tags:
        result["TagSet"] = [{"Key": k, "Value": v} for k, v in tags.items()]
    if result.get("CreatedTimestamp"):
        result["created_time"] = datetime.utcfromtimestamp(
            int(result["CreatedTimestamp"])
        ).isoformat()
    if result.get("LastModifiedTimestamp"):
        result["updated_time"] = datetime.utcfromtimestamp(
            int(result["LastModifiedTimestamp"])
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
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
        )
        bucket_location = bucket_location_res.get("LocationConstraint", fallback_region)
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
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
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
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
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
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
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
    )

    client.attach_role_policy(RoleName=role.get("RoleName"), PolicyArn=policy_arn)
    log_data["message"] = "Applied managed policy to role"
    log.debug(log_data)
    stats.count(
        f"{function}.attach_role_policy",
        tags={"role": role.get("Arn"), "policy": policy_arn},
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
        session_name="create_role_" + username,
    )
    results = {"errors": 0, "role_created": "false", "action_results": []}
    try:
        await sync_to_async(iam_client.create_role)(
            RoleName=create_model.role_name,
            AssumeRolePolicyDocument=json.dumps(default_trust_policy),
            Description=description,
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
        session_name="clone_role_" + username,
    )
    results = {"errors": 0, "role_created": "false", "action_results": []}
    try:
        await sync_to_async(iam_client.create_role)(
            RoleName=clone_model.dest_role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=description,
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
    """Given an ARN string, return the service """
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
    )

    regions = await sync_to_async(client.describe_regions)()
    return {r["RegionName"] for r in regions["Regions"]}


async def access_analyzer_validate_policy(
    policy: str, log_data, policy_type: str = "IDENTITY_POLICY"
) -> List[Dict[str, Any]]:
    try:
        enhanced_findings = []
        client = await sync_to_async(boto3.client)(
            "accessanalyzer", region_name=config.region
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

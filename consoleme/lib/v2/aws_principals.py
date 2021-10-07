from datetime import datetime, timedelta
from typing import List, Optional, Union

import ujson as json
from asgiref.sync import sync_to_async
from policy_sentry.util.arns import parse_arn

from consoleme.config import config
from consoleme.lib.account_indexers import get_account_id_to_name_mapping
from consoleme.lib.crypto import Crypto
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.policies import get_aws_config_history_url_for_resource
from consoleme.lib.redis import RedisHandler, redis_get
from consoleme.models import (
    AwsPrincipalModel,
    CloudTrailDetailsModel,
    CloudTrailError,
    CloudTrailErrorArray,
    EligibleRolesModel,
    EligibleRolesModelArray,
    ExtendedAwsPrincipalModel,
    S3DetailsModel,
    S3Error,
    S3ErrorArray,
)

stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
log = config.get_logger()
crypto = Crypto()
auth = get_plugin_by_name(config.get("plugins.auth", "default_auth"))()
aws = get_plugin_by_name(config.get("plugins.aws", "default_aws"))()
internal_policies = get_plugin_by_name(
    config.get("plugins.internal_policies", "default_policies")
)()
red = RedisHandler().redis_sync()


async def get_config_timeline_url_for_role(role, account_id):
    resource_id = role.get("resourceId")
    if resource_id:
        config_history_url = await get_aws_config_history_url_for_resource(
            account_id, resource_id, role["arn"], "AWS::IAM::Role"
        )
        return config_history_url


async def get_cloudtrail_details_for_role(arn: str):
    """
    Retrieves CT details associated with role, if they exist exists
    :param arn:
    :return:
    """
    error_url = config.get("cloudtrail_errors.error_messages_by_role_uri", "").format(
        arn=arn
    )

    errors_unformatted = await internal_policies.get_errors_by_role(
        arn, config.get("policies.number_cloudtrail_errors_to_display", 5)
    )

    ct_errors = []

    for event_string, value in errors_unformatted.items():
        event_call = event_string
        resource = None
        generated_policy = value.get("generated_policy", None)
        if "|||" in event_string:
            event_call, resource = event_string.split("|||")

        ct_errors.append(
            CloudTrailError(
                event_call=event_call,
                resource=resource,
                generated_policy=generated_policy,
                count=value.get("count", 0),
            )
        )

    return CloudTrailDetailsModel(
        error_url=error_url, errors=CloudTrailErrorArray(cloudtrail_errors=ct_errors)
    )


async def get_s3_details_for_role(account_id: str, role_name: str) -> S3DetailsModel:
    """
    Retrieves s3 details associated with role, if it exists
    :param arn:
    :return:
    """
    arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y%m%d")
    error_url = config.get("s3.query_url", "").format(
        yesterday=yesterday, role_name=f"'{role_name}'", account_id=f"'{account_id}'"
    )
    query_url = config.get("s3.non_error_query_url", "").format(
        yesterday=yesterday, role_name=f"'{role_name}'", account_id=f"'{account_id}'"
    )

    s3_error_topic = config.get("redis.s3_errors", "S3_ERRORS")
    all_s3_errors = await redis_get(s3_error_topic)
    s3_errors_unformatted = []
    if all_s3_errors:
        s3_errors_unformatted = json.loads(all_s3_errors).get(arn, [])
    s3_errors_formatted = []
    for error in s3_errors_unformatted:
        s3_errors_formatted.append(
            S3Error(
                count=error.get("count", ""),
                bucket_name=error.get("bucket_name", ""),
                request_prefix=error.get("request_prefix", ""),
                error_call=error.get("error_call", ""),
                status_code=error.get("status_code", ""),
                status_text=error.get("status_text", ""),
                role_arn=arn,
            )
        )

    return S3DetailsModel(
        query_url=query_url,
        error_url=error_url,
        errors=S3ErrorArray(s3_errors=s3_errors_formatted),
    )


async def get_app_details_for_role(arn: str):
    """
    Retrieves applications associated with role, if they exist
    :param arn:
    :return:
    """
    return await internal_policies.get_applications_associated_with_role(arn)


async def get_role_template(arn: str):
    return await sync_to_async(red.hget)(
        config.get("templated_roles.redis_key", "TEMPLATED_ROLES_v2"), arn.lower()
    )


async def get_user_details(
    account_id: str, user_name: str, extended: bool = False, force_refresh: bool = False
) -> Optional[Union[ExtendedAwsPrincipalModel, AwsPrincipalModel]]:
    account_ids_to_name = await get_account_id_to_name_mapping()
    arn = f"arn:aws:iam::{account_id}:user/{user_name}"
    user = await aws.fetch_iam_user(account_id, arn)
    # requested user doesn't exist
    if not user:
        return None
    if extended:
        return ExtendedAwsPrincipalModel(
            name=user_name,
            account_id=account_id,
            account_name=account_ids_to_name.get(account_id, None),
            arn=arn,
            inline_policies=user.get("UserPolicyList", []),
            config_timeline_url=await get_config_timeline_url_for_role(
                user, account_id
            ),
            cloudtrail_details=await get_cloudtrail_details_for_role(arn),
            s3_details=await get_s3_details_for_role(
                account_id=account_id, role_name=user_name
            ),
            apps=await get_app_details_for_role(arn),
            managed_policies=user["AttachedManagedPolicies"],
            groups=user["Groups"],
            tags=user["Tags"],
            owner=user.get("owner"),
            templated=False,
            template_link=None,
            created_time=str(user.get("CreateDate", "")),
            last_used_time=user.get("RoleLastUsed", {}).get("LastUsedDate"),
            description=user.get("Description"),
            permissions_boundary=user.get("PermissionsBoundary", {}),
        )
    else:
        return AwsPrincipalModel(
            name=user_name,
            account_id=account_id,
            account_name=account_ids_to_name.get(account_id, None),
            arn=arn,
        )


async def get_role_details(
    account_id: str, role_name: str, extended: bool = False, force_refresh: bool = False
) -> Optional[Union[ExtendedAwsPrincipalModel, AwsPrincipalModel]]:
    account_ids_to_name = await get_account_id_to_name_mapping()
    arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    role = await aws.fetch_iam_role(account_id, arn, force_refresh=force_refresh)
    # requested role doesn't exist
    if not role:
        return None
    if extended:
        template = await get_role_template(arn)
        return ExtendedAwsPrincipalModel(
            name=role_name,
            account_id=account_id,
            account_name=account_ids_to_name.get(account_id, None),
            arn=arn,
            inline_policies=role["policy"].get(
                "RolePolicyList", role["policy"].get("UserPolicyList", [])
            ),
            assume_role_policy_document=role["policy"]["AssumeRolePolicyDocument"],
            config_timeline_url=await get_config_timeline_url_for_role(
                role, account_id
            ),
            cloudtrail_details=await get_cloudtrail_details_for_role(arn),
            s3_details=await get_s3_details_for_role(
                account_id=account_id, role_name=role_name
            ),
            apps=await get_app_details_for_role(arn),
            managed_policies=role["policy"]["AttachedManagedPolicies"],
            tags=role["policy"]["Tags"],
            templated=bool(template),
            template_link=template,
            created_time=role["policy"].get("CreateDate"),
            last_used_time=role["policy"].get("RoleLastUsed", {}).get("LastUsedDate"),
            description=role["policy"].get("Description"),
            owner=role.get("owner"),
            permissions_boundary=role["policy"].get("PermissionsBoundary", {}),
        )
    else:
        return AwsPrincipalModel(
            name=role_name,
            account_id=account_id,
            account_name=account_ids_to_name.get(account_id, None),
            arn=arn,
        )


async def get_eligible_role_details(
    eligible_roles: List[str],
) -> EligibleRolesModelArray:
    account_ids_to_name = await get_account_id_to_name_mapping()
    eligible_roles_detailed = []
    for role in eligible_roles:
        arn_parsed = parse_arn(role)
        account_id = arn_parsed["account"]
        role_name = (
            arn_parsed["resource_path"]
            if arn_parsed["resource_path"]
            else arn_parsed["resource"]
        )
        account_friendly_name = account_ids_to_name.get(account_id, "Unknown")
        role_apps = await get_app_details_for_role(role)
        eligible_roles_detailed.append(
            EligibleRolesModel(
                arn=role,
                account_id=account_id,
                account_friendly_name=account_friendly_name,
                role_name=role_name,
                apps=role_apps,
            )
        )

    return EligibleRolesModelArray(roles=eligible_roles_detailed)

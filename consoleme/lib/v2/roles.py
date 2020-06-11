from datetime import datetime, timedelta

import ujson as json
from asgiref.sync import sync_to_async

from consoleme.config import config
from consoleme.lib.crypto import Crypto
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.redis import RedisHandler, redis_get
from consoleme.models import (
    CloudTrailDetailsModel,
    CloudTrailError,
    CloudTrailErrorArray,
    ExtendedRoleModel,
    S3DetailsModel,
    S3Error,
    S3ErrorArray,
)

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()
crypto = Crypto()
auth = get_plugin_by_name(config.get("plugins.auth"))()
aws = get_plugin_by_name(config.get("plugins.aws"))()
internal_policies = get_plugin_by_name(config.get("plugins.internal_policies"))()
red = RedisHandler().redis_sync()
account_ids_to_names = aws.get_account_ids_to_names()


async def get_cloudtrail_details_for_role(arn: str):
    """
    Retrieves CT details associated with role, if they exist exists
    :param arn:
    :return:
    """
    error_url = config.get("cloudtrail_errors.error_messages_by_role_uri").format(
        arn=arn
    )

    errors_unformatted = await internal_policies.get_errors_by_role(
        arn, config.get("policies.number_cloudtrail_errors_to_display", 5)
    )

    ct_errors = []

    for error in errors_unformatted:
        ct_errors.append(
            CloudTrailError(event_call=error["event_call"], count=error["count"])
        )

    return CloudTrailDetailsModel(
        error_url=error_url, errors=CloudTrailErrorArray(cloudtrail_errors=ct_errors)
    )


async def get_s3_details_for_role(account_id: str, role_name: str):
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
                count=error["count"],
                bucket_name=error["bucket_name"],
                request_prefix=error["request_prefix"],
                operation=error["operation"],
                error_status=error["error_status"],
                error_code=error["error_code"],
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


async def get_role_details(
    account_id: str, role_name: str, extended: bool = False
) -> ExtendedRoleModel:
    arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    role = await aws.fetch_iam_role(account_id, arn)
    template = await get_role_template(arn)
    return ExtendedRoleModel(
        name=role_name,
        account_id=account_id,
        account_name=account_ids_to_names.get(account_id, [None])[0],
        arn=arn,
        inline_policies=role["policy"]["RolePolicyList"],
        assume_role_policies=role["policy"]["AssumeRolePolicyDocument"],
        cloudtrail_details=await get_cloudtrail_details_for_role(arn),
        s3_details=await get_s3_details_for_role(
            account_id=account_id, role_name=role_name
        ),
        app_details=await get_app_details_for_role(arn),
        managed_policies=role["policy"]["AttachedManagedPolicies"],
        tags=role["policy"]["Tags"],
        templated=True if template else False,
        template_link=template,
    )

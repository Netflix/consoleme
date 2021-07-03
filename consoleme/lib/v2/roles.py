import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional, Union, List, Dict, Any

import sentry_sdk
import ujson as json
from asgiref.sync import sync_to_async

from consoleme.config import config
from consoleme.lib.account_indexers import get_account_id_to_name_mapping
from consoleme.lib.cache import retrieve_json_data_from_redis_or_s3
from consoleme.lib.crypto import Crypto
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.policies import get_aws_config_history_url_for_resource
from consoleme.lib.redis import RedisHandler, redis_get
from consoleme.lib.singleton import Singleton
from consoleme.models import (
    CloudTrailDetailsModel,
    CloudTrailError,
    CloudTrailErrorArray,
    ExtendedRoleModel,
    RoleModel,
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


class RoleCache(metaclass=Singleton):
    def __init__(self) -> None:
        self._lock: Lock = Lock()
        self._last_update: int = 0
        self._all_roles: List[str] = []
        self._roles_by_account: Dict[str, List[str]] = defaultdict(list)
        self._roles_by_name: Dict[str, List[str]] = defaultdict(list)

    async def all_roles(self) -> List[str]:
        await self.populate()
        return self._all_roles

    async def roles_by_account(self) -> Dict[str, List[str]]:
        await self.populate()
        return self._roles_by_account

    async def roles_by_name(self) -> Dict[str, List[str]]:
        await self.populate()
        return self._roles_by_name

    async def roles_in_account(self, account: str) -> List[str]:
        await self.populate()
        return self._roles_by_account.get(account, [])

    async def roles_with_name(self, name: str) -> List[str]:
        await self.populate()
        return self._roles_by_name.get(name, [])

    def _update_mappings(self) -> None:
        for role in self._all_roles:
            account = role.split(":")[4]
            name = role.split("/")[-1]
            self._roles_by_account[account].append(role)
            self._roles_by_name[name].append(role)

    def _parse_roles(self, config_data: Dict[str, Any]) -> None:
        for arn in config_data.keys():
            if ':iam:' in arn and ':role/' in arn:
                self._all_roles.append(arn)

    async def populate(self) -> None:
        if not self._all_roles or int(time.time()) - self._last_update > 60:
            self._lock.acquire()
            redis_topic = config.get(
                "aws_config_cache.redis_key", "AWSCONFIG_RESOURCE_CACHE"
            )
            s3_bucket = config.get("aws_config_cache_combined.s3.bucket")
            s3_key = config.get(
                "aws_config_cache_combined.s3.file",
                "aws_config_cache_combined/aws_config_resource_cache_combined_v1.json.gz",
            )
            try:
                config_data = await retrieve_json_data_from_redis_or_s3(
                    # redis_topic,
                    s3_bucket=s3_bucket,
                    s3_key=s3_key,
                )
            except Exception as e:
                sentry_sdk.capture_exception()
                log.error(
                    {
                        "function": f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
                        "error": f"Error loading config data. Returning empty mapping: {e}",
                    },
                    exc_info=True,
                )
                self._lock.release()
                return
            self._parse_roles(config_data)
            self._update_mappings()
            self._lock.release()


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
        event_call, resource = event_string.split("|||")
        ct_errors.append(
            CloudTrailError(
                event_call=event_call,
                resource=resource,
                generated_policy=value.get("generated_policy"),
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


async def get_role_details(
    account_id: str, role_name: str, extended: bool = False, force_refresh: bool = False
) -> Optional[Union[ExtendedRoleModel, RoleModel]]:
    account_ids_to_name = await get_account_id_to_name_mapping()
    arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    role = await aws.fetch_iam_role(account_id, arn, force_refresh=force_refresh)
    # requested role doesn't exist
    if not role:
        return None
    if extended:
        template = await get_role_template(arn)
        return ExtendedRoleModel(
            name=role_name,
            account_id=account_id,
            account_name=account_ids_to_name.get(account_id, None),
            arn=arn,
            inline_policies=role["policy"]["RolePolicyList"],
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
            permissions_boundary=role["policy"].get("PermissionsBoundary", {}),
        )
    else:
        return RoleModel(
            name=role_name,
            account_id=account_id,
            account_name=account_ids_to_name.get(account_id, None),
            arn=arn,
        )

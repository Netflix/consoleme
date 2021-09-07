import sys
import time
from collections import defaultdict
from typing import Dict, List, Optional

import sentry_sdk
from pydantic.json import pydantic_encoder

from consoleme.config import config
from consoleme.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from consoleme.lib.cloud_credential_authorization_mapping.dynamic_config import (
    DynamicConfigAuthorizationMappingGenerator,
)
from consoleme.lib.cloud_credential_authorization_mapping.internal_plugin import (
    InternalPluginAuthorizationMappingGenerator,
)
from consoleme.lib.cloud_credential_authorization_mapping.models import (
    RoleAuthorizations,
    RoleAuthorizationsDecoder,
    user_or_group,
)
from consoleme.lib.cloud_credential_authorization_mapping.role_tags import (
    RoleTagAuthorizationMappingGenerator,
)
from consoleme.lib.singleton import Singleton

log = config.get_logger("consoleme")


class CredentialAuthorizationMapping(metaclass=Singleton):
    def __init__(self) -> None:
        self._all_roles = []
        self._all_roles_count = 0
        self._all_roles_last_update = 0
        self.authorization_mapping = {}
        self.authorization_mapping_last_update = 0
        self.reverse_mapping = {}
        self.reverse_mapping_last_update = 0

    async def retrieve_credential_authorization_mapping(
        self, max_age: Optional[int] = None
    ):
        """
        This function retrieves the credential authorization mapping. This is a mapping of users/groups to the IAM roles
        they are allowed to get credentials for. This is the authoritative mapping that ConsoleMe uses for access.

        :param max_age: Maximum allowable age of the credential authorization mapping. If the mapping is older than
        `max_age` seconds, this function will raise an exception and return an empty mapping.
        """
        if (
            not self.authorization_mapping
            or int(time.time()) - self.authorization_mapping_last_update > 60
        ):
            redis_topic = config.get(
                "generate_and_store_credential_authorization_mapping.redis_key",
                "CREDENTIAL_AUTHORIZATION_MAPPING_V1",
            )
            s3_bucket = config.get(
                "generate_and_store_credential_authorization_mapping.s3.bucket"
            )
            s3_key = config.get(
                "generate_and_store_credential_authorization_mapping.s3.file",
                "credential_authorization_mapping/credential_authorization_mapping_v1.json.gz",
            )
            try:
                self.authorization_mapping = await retrieve_json_data_from_redis_or_s3(
                    redis_topic,
                    s3_bucket=s3_bucket,
                    s3_key=s3_key,
                    json_object_hook=RoleAuthorizationsDecoder,
                    json_encoder=pydantic_encoder,
                    max_age=max_age,
                )
                self.authorization_mapping_last_update = int(time.time())
            except Exception as e:
                sentry_sdk.capture_exception()
                log.error(
                    {
                        "function": f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
                        "error": f"Error loading cloud credential mapping. Returning empty mapping: {e}",
                    },
                    exc_info=True,
                )
                return {}
        return self.authorization_mapping

    async def retrieve_reverse_authorization_mapping(
        self, max_age: Optional[int] = None
    ):
        """
        This function retrieves the inverse of the credential authorization mapping. This is a mapping of IAM roles
        to the users/groups that are allowed to access them. This mapping is used primarily for auditing.

        :param max_age: Maximum allowable age of the reverse credential authorization mapping. If the mapping is older
        than `max_age` seconds, this function will raise an exception and return an empty mapping.
        """
        if (
            not self.reverse_mapping
            or int(time.time()) - self.reverse_mapping_last_update > 60
        ):
            redis_topic = config.get(
                "generate_and_store_reverse_authorization_mapping.redis_key",
                "REVERSE_AUTHORIZATION_MAPPING_V1",
            )
            s3_bucket = config.get(
                "generate_and_store_reverse_authorization_mapping.s3.bucket"
            )
            s3_key = config.get(
                "generate_and_store_reverse_authorization_mapping.s3.file",
                "reverse_authorization_mapping/reverse_authorization_mapping_v1.json.gz",
            )
            try:
                self.reverse_mapping = await retrieve_json_data_from_redis_or_s3(
                    redis_topic,
                    s3_bucket=s3_bucket,
                    s3_key=s3_key,
                    json_object_hook=RoleAuthorizationsDecoder,
                    json_encoder=pydantic_encoder,
                    max_age=max_age,
                )
                self.reverse_mapping_last_update = int(time.time())
            except Exception as e:
                sentry_sdk.capture_exception()
                log.error(
                    {
                        "function": f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
                        "error": f"Error loading reverse credential mapping. Returning empty mapping: {e}",
                    },
                    exc_info=True,
                )
                return {}
        return self.reverse_mapping

    async def retrieve_all_roles(self, max_age: Optional[int] = None):
        if not self._all_roles or int(time.time()) - self._all_roles_last_update > 600:
            redis_topic = config.get("aws.iamroles_redis_key", "IAM_ROLE_CACHE")
            s3_bucket = config.get(
                "cache_iam_resources_across_accounts.all_roles_combined.s3.bucket"
            )
            s3_key = config.get(
                "cache_iam_resources_across_accounts.all_roles_combined.s3.file",
                "account_resource_cache/cache_all_roles_v1.json.gz",
            )
            try:
                all_roles = await retrieve_json_data_from_redis_or_s3(
                    redis_topic,
                    redis_data_type="hash",
                    s3_bucket=s3_bucket,
                    s3_key=s3_key,
                    json_object_hook=RoleAuthorizationsDecoder,
                    json_encoder=pydantic_encoder,
                    max_age=max_age,
                )
            except Exception as e:
                sentry_sdk.capture_exception()
                log.error(
                    {
                        "function": f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
                        "error": f"Error loading IAM roles. Returning empty list: {e}",
                    },
                    exc_info=True,
                )
                return []
            self._all_roles = list(all_roles.keys())
            self._all_roles_count = len(self._all_roles)
            self._all_roles_last_update = int(time.time())
        return self._all_roles

    async def all_roles(self, paginate=False, page=None, count=None):
        all_roles = await self.retrieve_all_roles()
        return all_roles

    async def number_roles(self) -> int:
        _ = await self.retrieve_all_roles()
        return self._all_roles_count

    async def determine_role_authorized_groups(self, account_id: str, role_name: str):
        arn = f"arn:aws:iam::{account_id}:role/{role_name.lower()}"
        reverse_mapping = await self.retrieve_reverse_authorization_mapping()
        groups = reverse_mapping.get(arn, [])
        return set(groups)

    async def determine_users_authorized_roles(self, user, groups, include_cli=False):
        authorization_mapping = await self.retrieve_credential_authorization_mapping()
        authorized_roles = set()
        user_mapping = authorization_mapping.get(user, [])
        if user_mapping:
            authorized_roles.update(user_mapping.authorized_roles)
            if include_cli:
                authorized_roles.update(user_mapping.authorized_roles_cli_only)
        for group in groups:
            group_mapping = authorization_mapping.get(group, [])
            if group_mapping:
                authorized_roles.update(group_mapping.authorized_roles)
                if include_cli:
                    authorized_roles.update(group_mapping.authorized_roles_cli_only)
        return sorted(authorized_roles)


async def generate_and_store_reverse_authorization_mapping(
    authorization_mapping: Dict[user_or_group, RoleAuthorizations]
) -> Dict[str, List[user_or_group]]:
    reverse_mapping = defaultdict(list)
    for identity, roles in authorization_mapping.items():
        for role in roles.authorized_roles:
            reverse_mapping[role.lower()].append(identity)
        for role in roles.authorized_roles_cli_only:
            reverse_mapping[role.lower()].append(identity)

    # Store in S3 and Redis
    redis_topic = config.get(
        "generate_and_store_reverse_authorization_mapping.redis_key",
        "REVERSE_AUTHORIZATION_MAPPING_V1",
    )
    s3_bucket = None
    s3_key = None
    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev", "test"]:
        s3_bucket = config.get(
            "generate_and_store_reverse_authorization_mapping.s3.bucket"
        )
        s3_key = config.get(
            "generate_and_store_reverse_authorization_mapping.s3.file",
            "reverse_authorization_mapping/reverse_authorization_mapping_v1.json.gz",
        )
    await store_json_results_in_redis_and_s3(
        reverse_mapping,
        redis_topic,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        json_encoder=pydantic_encoder,
    )
    return reverse_mapping


async def generate_and_store_credential_authorization_mapping() -> Dict[
    user_or_group, RoleAuthorizations
]:
    authorization_mapping: Dict[user_or_group, RoleAuthorizations] = {}

    if config.get("cloud_credential_authorization_mapping.role_tags.enabled", True):
        authorization_mapping = await RoleTagAuthorizationMappingGenerator().generate_credential_authorization_mapping(
            authorization_mapping
        )
    if config.get(
        "cloud_credential_authorization_mapping.dynamic_config.enabled", True
    ):
        authorization_mapping = await DynamicConfigAuthorizationMappingGenerator().generate_credential_authorization_mapping(
            authorization_mapping
        )
    if config.get(
        "cloud_credential_authorization_mapping.internal_plugin.enabled", False
    ):
        authorization_mapping = await InternalPluginAuthorizationMappingGenerator().generate_credential_authorization_mapping(
            authorization_mapping
        )

    # Store in S3 and Redis
    redis_topic = config.get(
        "generate_and_store_credential_authorization_mapping.redis_key",
        "CREDENTIAL_AUTHORIZATION_MAPPING_V1",
    )
    s3_bucket = None
    s3_key = None
    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev", "test"]:
        s3_bucket = config.get(
            "generate_and_store_credential_authorization_mapping.s3.bucket"
        )
        s3_key = config.get(
            "generate_and_store_credential_authorization_mapping.s3.file",
            "credential_authorization_mapping/credential_authorization_mapping_v1.json.gz",
        )
    await store_json_results_in_redis_and_s3(
        authorization_mapping,
        redis_topic,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        json_encoder=pydantic_encoder,
    )
    return authorization_mapping

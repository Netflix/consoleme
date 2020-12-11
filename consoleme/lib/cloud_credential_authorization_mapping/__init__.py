import sys
import time
from typing import Dict

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
        self.authorization_mapping = {}
        self.last_update = 0

    async def retrieve_credential_authorization_mapping(self):
        if not self.authorization_mapping or int(time.time()) - self.last_update > 60:
            redis_topic = config.get(
                "generate_and_store_credential_authorization_mapping.redis_key",
                "CREDENTIAL_AUTHORIZATION_MAPPING_V1",
            )
            s3_bucket = config.get(
                "generate_and_store_credential_authorization_mapping.s3.bucket"
            )
            s3_key = config.get(
                "generate_and_store_credential_authorization_mapping.s3.file"
            )
            try:
                self.authorization_mapping = await retrieve_json_data_from_redis_or_s3(
                    redis_topic,
                    s3_bucket=s3_bucket,
                    s3_key=s3_key,
                    json_object_hook=RoleAuthorizationsDecoder,
                    json_encoder=pydantic_encoder,
                )
                self.last_update = int(time.time())
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
            "generate_and_store_credential_authorization_mapping.s3.file"
        )
    await store_json_results_in_redis_and_s3(
        authorization_mapping,
        redis_topic,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        json_encoder=pydantic_encoder,
    )
    return authorization_mapping

"""Group mapping plugin."""
import time

import simplejson as json
from redis.exceptions import ConnectionError

from consoleme.config import config
from consoleme.lib.crypto import Crypto
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.redis import RedisHandler

log = config.get_logger("consoleme")
aws = get_plugin_by_name(config.get("plugins.aws"))()
stats = get_plugin_by_name(config.get("plugins.metrics"))()


# TODO: Docstrings should provide examples of the data that needs to be returned


class GroupMapping:
    """Group mapping handles mapping groups to eligible roles and accounts."""

    def __init__(self):
        pass

    async def get_eligible_roles(
        self, username: str, groups: list, user_role: str, console_only: bool, **kwargs
    ) -> list:
        """Get eligible roles for user."""
        roles: list = []

        if config.get("get_eligible_roles.from_config"):
            roles.extend(
                await self.get_eligible_roles_from_config(
                    username, groups, console_only
                )
            )
        return list(set(roles))

    @staticmethod
    async def filter_eligible_roles(query: str, obj: object) -> list:
        return []

    async def set_recent_user(self, user):
        pass

    async def set_console_roles_in_cache(
        self,
        user,
        roles,
        expiration=config.get("group_mapping_config.role_cache_expiration", 21600),
    ):
        """Set roles in cache with a nominal expiration"""
        stats.count("set_console_roles_in_cache")
        if not self.red:
            self.red = await RedisHandler().redis()
        expiration = int(time.time()) + expiration
        role_blob = json.dumps({"user": user, "roles": roles, "expiration": expiration})
        crypto = Crypto()
        sig = crypto.sign(role_blob)

        key = config.get(
            "group_mapping_config.role_cache_redis_key", "ROLE_CACHE_{}"
        ).format(user)
        sig_key = config.get(
            "group_mapping_config.role_cache_redis_sig_key", "ROLE_CACHE_SIG_{}"
        ).format(user)

        try:
            self.red.setex(key, expiration, role_blob)
            self.red.setex(sig_key, expiration, sig)
        except ConnectionError:
            log.error("Error connecting to Redis.", exc_info=True)

    async def get_roles_from_cache(self, user):
        """Get roles from cache"""
        stats.count("get_roles_from_cache")

        key = config.get(
            "group_mapping_config.role_cache_redis_key", "ROLE_CACHE_{}"
        ).format(user)
        sig_key = config.get(
            "group_mapping_config.role_cache_redis_sig_key", "ROLE_CACHE_SIG_{}"
        ).format(user)

        if not self.red:
            self.red = await RedisHandler().redis()

        role_r = self.red.get(key)
        if not role_r:
            return []

        role_sig = self.red.get(sig_key)

        if not role_sig:
            stats.count("get_roles_from_cache.no_role_sig")
            log.error("Role data is in redis, but no signature is present.")
            return []

        role_blob = json.loads(role_r)

        if int(time.time()) > role_blob.get("expiration", 0):
            stats.count("get_roles_from_cache.role_cache_expired")
            log.error("Role cache for {} has expired.".format(user))
            return []

        if role_blob.get("user") != user:
            stats.count("get_roles_from_cache.role_cache_user_invalid")
            log.error(
                "Role cache user mismatch. Cache has: {}. User requested is {}".format(
                    role_blob.get("user"), user
                )
            )
            return []
        return role_blob.get("roles")

    async def get_eligible_roles_from_group_prefix(self, groups) -> list:
        """Get eligible roles for user from group header prefix."""
        return []

    async def get_eligible_roles_from_config(self, user, groups, console_only):
        """Get eligible roles from configuration."""
        stats.count("get_eligible_roles_from_config")
        roles = []
        group_mapping = config.get("dynamic_config.group_mapping")

        if not group_mapping:
            return roles

        # First check configuration for user-specific entries
        eligible_roles = group_mapping.get(user, {}).get("roles", [])
        roles.extend(eligible_roles)
        if not console_only:
            eligible_cli_roles = group_mapping.get(user, {}).get("cli_only_roles", [])
            roles.extend(eligible_cli_roles)

        # Check configuration for any allowances based on user's groups
        for g in groups:
            eligible_roles = group_mapping.get(g, {}).get("roles", [])
            roles.extend(eligible_roles)
            if not console_only:
                eligible_cli_roles = group_mapping.get(g, {}).get("cli_only_roles", [])
                roles.extend(eligible_cli_roles)

        return roles

    async def get_eligible_accounts(self, role_arns):
        """Get eligible accounts for user."""
        stats.count("get_eligible_accounts")
        account_ids = {}

        friendly_names = aws.get_account_ids_to_names()
        for r in role_arns:
            account_id = r.split(":")[4]
            account_friendlyname = friendly_names.get(account_id, "")
            if account_friendlyname and isinstance(account_friendlyname, list):
                account_ids[account_id] = account_friendlyname[0]
        return account_ids

    async def get_account_mappings(self) -> dict:
        """Get a dictionary with all of the account mappings (friendly names -> ID and ID -> names)."""
        return {}

    async def get_secondary_approvers(self, group, return_default=False):
        return config.get("access_requests.default_approver")

    def get_account_names_to_ids(self, force_refresh: bool = False) -> dict:
        """Get account name to id mapping"""
        stats.count("get_account_names_to_ids")
        return {}

    def get_account_ids_to_names(self, force_refresh: bool = False) -> str:
        """Get account id to name mapping"""
        stats.count("get_account_ids_to_names")
        return {}

    async def get_max_cert_age_for_role(self, role_name: str):
        """Retrieve the maximum allowed certificate age allowable to retrieve a particular
        role. 30 will be returned if there is no max age defined.
        """
        return 360

    async def get_all_account_data(self):
        return {}

    async def get_all_accounts(self):
        """Get all account details"""
        return {}

    async def get_all_user_groups(self, user, groups):
        return []

    def is_role_valid(self, entry):
        return True


def init():
    """Initialize group_mapping plugin."""
    return GroupMapping()

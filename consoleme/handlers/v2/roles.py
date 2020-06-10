import ujson as json

from consoleme.config import config
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.lib.crypto import Crypto
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.v2.roles import get_role_details

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()
crypto = Crypto()
auth = get_plugin_by_name(config.get("plugins.auth"))()
aws = get_plugin_by_name(config.get("plugins.aws"))()
internal_policies = get_plugin_by_name(config.get("plugins.internal_policies"))()


class RolesHandler(BaseAPIV2Handler):
    """Handler for /api/v2/roles

    Allows read access to a list of roles across all accounts. Returned roles are
    limited to what the requesting user has access to.
    """

    allowed_methods = ["GET"]

    def initialize(self):
        self.user: str = None
        self.eligible_roles: list = []

    async def get(self):
        payload = {
            "eligible_roles": self.eligible_roles,
            "_xsrf": self.xsrf_token.decode("utf-8"),
        }
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(payload, escape_forward_slashes=False))
        await self.finish()


class AccountRolesHandler(BaseAPIV2Handler):
    """Handler for /api/v2/roles/{account_number}

    Allows read access to a list of roles by account. Roles are limited to what the
    requesting user has access to.
    """

    allowed_methods = ["GET"]

    async def get(self, account_id):
        """
        GET /api/v2/roles/{account_id}
        """
        log_data = {
            "function": "AccountRolesHandler.get",
            "user": self.user,
            "message": "Writing all eligible user roles",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Get roles by account")


class RoleDetailHandler(BaseAPIV2Handler):
    """Handler for /api/v2/roles/{accountNumber}/{roleName}

    Allows read and update access to a specific role in an account.
    """

    allowed_methods = ["GET", "PUT"]

    async def get(self, account_id, role_name):
        """
        GET /api/v2/roles/{account_number}/{role_name}
        """
        log_data = {
            "function": "RoleDetailHandler.get",
            "user": self.user,
            "ip": self.ip,
            "message": "Retrieving role details",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "account_id": account_id,
            "role_name": role_name,
        }
        stats.count(
            "RoleDetailHandler.get",
            tags={"user": self.user, "account_id": account_id, "role_name": role_name},
        )
        log.debug(log_data)
        role_details = await get_role_details(account_id, role_name)

        if not role_details:
            self.send_error(
                404,
                message=f"Unable to retrieve the specified role: {account_id}/{role_name}",
            )
            return

        self.write(role_details.dict())

    async def put(self, account_id, role_name):
        """
        PUT /api/v2/roles/{account_number}/{role_name}
        """
        log_data = {
            "function": "RoleDetailHandler.put",
            "user": self.user,
            "message": "Writing all eligible user roles",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Update role details")

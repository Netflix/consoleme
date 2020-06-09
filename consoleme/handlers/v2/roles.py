import sys

import ujson as json

from consoleme.config import config
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.lib.aws import can_delete_roles, delete_iam_role
from consoleme.lib.crypto import Crypto
from consoleme.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()
crypto = Crypto()
auth = get_plugin_by_name(config.get("plugins.auth"))()
aws = get_plugin_by_name(config.get("plugins.aws"))()


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

    allowed_methods = ["GET", "PUT", "DELETE"]

    async def get(self, account_number, role_name):
        """
        GET /api/v2/roles/{account_number}/{role_name}
        """
        log_data = {
            "function": "RoleDetailHandler.get",
            "user": self.user,
            "message": "Writing all eligible user roles",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Get role details")

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

    async def delete(self, account_id, role_name):
        """
        DELETE /api/v2/roles/{account_id}/{role_name}
        """
        if not self.user:
            self.write_error(403, message="No user detected")
            return

        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "ip": self.ip,
            "account": account_id,
            "role": role_name,
        }

        allowed_to_delete = await can_delete_roles(self.groups)
        if not allowed_to_delete:
            stats.count(
                f"{log_data['function']}.unauthorized",
                tags={
                    "user": self.user,
                    "account": account_id,
                    "role": role_name,
                    "authorized": False,
                    "ip": self.ip,
                },
            )
            log_data["message"] = "User is unauthorized to delete a role"
            log.error(log_data)
            self.write_error(403, message="User is unauthorized to delete a role")
            return
        try:
            await delete_iam_role(account_id, role_name, self.user)
        except Exception as e:
            log_data["message"] = "Exception deleting role"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.exception",
                tags={
                    "user": self.user,
                    "account": account_id,
                    "role": role_name,
                    "authorized": True,
                    "ip": self.ip,
                },
            )
            self.write_error(500, message="Error occurred deleting role: " + str(e))
            return

        # if here, role has been successfully deleted
        arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        await aws.fetch_iam_role(account_id, arn, force_refresh=True)
        response_json = {
            "status": "success",
            "message": "Successfully deleted role from account",
            "role": role_name,
            "account": account_id,
        }
        self.write(json.dumps(response_json))

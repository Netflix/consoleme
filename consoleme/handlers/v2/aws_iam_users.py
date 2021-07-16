import sys
from typing import Optional

import sentry_sdk
import tornado.escape

from consoleme.config import config
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.lib.auth import can_delete_roles
from consoleme.lib.aws import delete_iam_role
from consoleme.lib.crypto import Crypto
from consoleme.lib.generic import str2bool
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.v2.roles import get_user_details

stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
log = config.get_logger()
crypto = Crypto()
auth = get_plugin_by_name(config.get("plugins.auth", "default_auth"))()
aws = get_plugin_by_name(config.get("plugins.aws", "default_aws"))()
group_mapping = get_plugin_by_name(
    config.get("plugins.group_mapping", "default_group_mapping")
)()
internal_policies = get_plugin_by_name(
    config.get("plugins.internal_policies", "default_policies")
)()


class UserDetailHandler(BaseAPIV2Handler):
    """Handler for /api/v2/users/{accountNumber}/{userName}

    Allows read and update access to a specific user in an account.
    """

    allowed_methods = ["GET", "PUT", "DELETE"]

    def initialize(self):
        self.user: Optional[str] = None
        self.eligible_roles: list = []

    async def get(self, account_id, user_name):
        """
        GET /api/v2/users/{account_number}/{user_name}
        """
        log_data = {
            "function": "UsersDetailHandler.get",
            "user": self.user,
            "ip": self.ip,
            "message": "Retrieving user details",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "account_id": account_id,
            "user_name": user_name,
        }
        stats.count(
            "UsersDetailHandler.get",
            tags={"user": self.user, "account_id": account_id, "user_name": user_name},
        )
        log.debug(log_data)
        force_refresh = str2bool(
            self.request.arguments.get("force_refresh", [False])[0]
        )

        error = ""

        try:
            user_details = await get_user_details(
                account_id, user_name, extended=True, force_refresh=force_refresh
            )
        except Exception as e:
            sentry_sdk.capture_exception()
            log.error({**log_data, "error": e}, exc_info=True)
            user_details = None
            error = str(e)

        if not user_details:
            self.send_error(
                404,
                message=f"Unable to retrieve the specified user: {account_id}/{user_name}. {error}",
            )
            return
        self.write(user_details.json())

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
        account_id = tornado.escape.xhtml_escape(account_id)
        role_name = tornado.escape.xhtml_escape(role_name)

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

        can_delete_role = can_delete_roles(self.user, self.groups)
        if not can_delete_role:
            stats.count(
                f"{log_data['function']}.unauthorized",
                tags={
                    "user": self.user,
                    "account": account_id,
                    "role": role_name,
                    "authorized": can_delete_role,
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
                    "authorized": can_delete_role,
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
        self.write(response_json)

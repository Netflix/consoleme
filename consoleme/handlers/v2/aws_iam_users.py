import sys
from typing import Optional

import sentry_sdk
import tornado.escape

from consoleme.config import config
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.lib.auth import can_delete_iam_principals
from consoleme.lib.aws import delete_iam_user
from consoleme.lib.generic import str2bool
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.v2.aws_principals import get_user_details

stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
log = config.get_logger()
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

    Allows read and delete access to a specific user in an account.
    """

    allowed_methods = ["GET", "DELETE"]

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

    async def delete(self, account_id, iam_user_name):
        """
        DELETE /api/v2/users/{account_id}/{iam_user_name}
        """
        account_id = tornado.escape.xhtml_escape(account_id)
        iam_user_name = tornado.escape.xhtml_escape(iam_user_name)

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
            "iam_user_name": iam_user_name,
        }

        can_delete_principal = can_delete_iam_principals(self.user, self.groups)
        if not can_delete_principal:
            stats.count(
                f"{log_data['function']}.unauthorized",
                tags={
                    "user": self.user,
                    "account": account_id,
                    "iam_user_name": iam_user_name,
                    "authorized": can_delete_principal,
                    "ip": self.ip,
                },
            )
            log_data["message"] = "User is unauthorized to delete an AWS IAM User"
            log.error(log_data)
            self.write_error(
                403, message="User is unauthorized to delete an AWS IAM user"
            )
            return
        try:
            await delete_iam_user(account_id, iam_user_name, self.user)
        except Exception as e:
            log_data["message"] = "Exception deleting AWS IAM User"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.exception",
                tags={
                    "user": self.user,
                    "account": account_id,
                    "iam_user_name": iam_user_name,
                    "authorized": can_delete_principal,
                    "ip": self.ip,
                },
            )
            self.write_error(500, message="Error occurred deleting IAM user: " + str(e))
            return

        # if here, user has been successfully deleted
        arn = f"arn:aws:iam::{account_id}:user/{iam_user_name}"
        await aws.fetch_iam_user(account_id, arn)
        response_json = {
            "status": "success",
            "message": "Successfully deleted AWS IAM user from account",
            "iam_user_name": iam_user_name,
            "account": account_id,
        }
        self.write(response_json)

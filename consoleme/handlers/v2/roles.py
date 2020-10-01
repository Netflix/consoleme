import sys

import sentry_sdk
import ujson as json
from pydantic import ValidationError

from consoleme.config import config
from consoleme.handlers.base import BaseAPIV2Handler, BaseMtlsHandler
from consoleme.lib.aws import (
    can_create_roles,
    can_delete_roles,
    can_delete_roles_app,
    clone_iam_role,
    create_iam_role,
    delete_iam_role,
)
from consoleme.lib.crypto import Crypto
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.v2.roles import get_role_details
from consoleme.models import CloneRoleRequestModel, RoleCreationRequestModel

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()
crypto = Crypto()
auth = get_plugin_by_name(config.get("plugins.auth"))()
aws = get_plugin_by_name(config.get("plugins.aws"))()
internal_policies = get_plugin_by_name(config.get("plugins.internal_policies"))()


class RolesHandler(BaseAPIV2Handler):
    """Handler for /api/v2/roles

    GET - Allows read access to a list of roles across all accounts. Returned roles are
    limited to what the requesting user has access to.
    POST - Allows (authorized) users to create a role
    """

    allowed_methods = ["GET", "POST"]

    async def get(self):
        payload = {"eligible_roles": self.eligible_roles}
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(payload, escape_forward_slashes=False))
        await self.finish()

    async def post(self):
        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "ip": self.ip,
        }
        can_create_role = await can_create_roles(self.groups, self.user)
        if not can_create_role:
            stats.count(
                f"{log_data['function']}.unauthorized",
                tags={"user": self.user, "authorized": can_create_role},
            )
            log_data["message"] = "User is unauthorized to create a role"
            log.error(log_data)
            self.write_error(403, message="User is unauthorized to create a role")
            return

        try:
            create_model = RoleCreationRequestModel.parse_raw(self.request.body)
        except ValidationError as e:
            log_data["message"] = "Validation Exception"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.validation_exception", tags={"user": self.user}
            )
            sentry_sdk.capture_exception()
            self.write_error(400, message="Error validating input: " + str(e))
            return

        try:
            results = await create_iam_role(create_model, self.user)
        except Exception as e:
            log_data["message"] = "Exception creating role"
            log_data["error"] = str(e)
            log_data["account_id"] = create_model.account_id
            log_data["role_name"] = create_model.role_name
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.exception",
                tags={
                    "user": self.user,
                    "account_id": create_model.account_id,
                    "role_name": create_model.role_name,
                },
            )
            sentry_sdk.capture_exception()
            self.write_error(500, message="Exception occurred cloning role: " + str(e))
            return

        # if here, role has been successfully cloned
        stats.count(
            f"{log_data['function']}.success",
            tags={
                "user": self.user,
                "account_id": create_model.account_id,
                "role_name": create_model.role_name,
            },
        )
        self.write(results)


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

    def initialize(self):
        self.user: str = None
        self.eligible_roles: list = []

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

        error = ""

        try:
            role_details = await get_role_details(account_id, role_name, extended=True)
        except Exception as e:
            log.error({**log_data, "error": e}, exc_info=True)
            role_details = None
            error = e

        if not role_details:
            self.send_error(
                404,
                message=f"Unable to retrieve the specified role: {account_id}/{role_name}. {error}",
            )
            return

        self.write(role_details.json())

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

        can_delete_role = await can_delete_roles(self.groups)
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


class RoleDetailAppHandler(BaseMtlsHandler):

    """Handler for /api/v2/mtls/roles/{accountNumber}/{roleName}

    Allows apps to delete a role
    """

    allowed_methods = ["DELETE"]

    def check_xsrf_cookie(self):
        pass

    async def delete(self, account_id, role_name):
        """
        DELETE /api/v2/mtls/roles/{account_id}/{role_name}
        """
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "account_id": account_id,
            "role_name": role_name,
        }
        requester_type = self.requester.get("type")
        if requester_type != "application":
            log_data[
                "message"
            ] = "Non-application trying to access application only endpoint"
            log.error(log_data)
            self.write_error(406, message="Endpoint not supported for non-applications")
            return

        app_name = self.requester.get("name")
        can_delete_role = await can_delete_roles_app(app_name)
        if not can_delete_role:
            stats.count(
                f"{log_data['function']}.unauthorized",
                tags={
                    "app_name": app_name,
                    "account_id": account_id,
                    "role_name": role_name,
                    "authorized": can_delete_role,
                },
            )
            log_data["message"] = "App is unauthorized to delete a role"
            log.error(log_data)
            self.write_error(403, message="App is unauthorized to delete a role")
            return

        try:
            await delete_iam_role(account_id, role_name, app_name)
        except Exception as e:
            log_data["message"] = "Exception deleting role"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.exception",
                tags={
                    "app_name": app_name,
                    "account_id": account_id,
                    "role_name": role_name,
                    "authorized": can_delete_role,
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


class RoleCloneHandler(BaseAPIV2Handler):
    """Handler for /api/v2/clone/role

    Allows cloning a role.
    """

    allowed_methods = ["POST"]

    async def post(self):

        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "ip": self.ip,
        }
        can_create_role = await can_create_roles(self.groups, self.user)
        if not can_create_role:
            stats.count(
                f"{log_data['function']}.unauthorized",
                tags={"user": self.user, "authorized": can_create_role},
            )
            log_data["message"] = "User is unauthorized to clone a role"
            log.error(log_data)
            self.write_error(403, message="User is unauthorized to clone a role")
            return

        try:
            clone_model = CloneRoleRequestModel.parse_raw(self.request.body)
        except ValidationError as e:
            log_data["message"] = "Validation Exception"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.validation_exception", tags={"user": self.user}
            )
            sentry_sdk.capture_exception()
            self.write_error(400, message="Error validating input: " + str(e))
            return

        try:
            results = await clone_iam_role(clone_model, self.user)
        except Exception as e:
            log_data["message"] = "Exception cloning role"
            log_data["error"] = str(e)
            log_data["account_id"] = clone_model.account_id
            log_data["role_name"] = clone_model.role_name
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.exception",
                tags={
                    "user": self.user,
                    "account_id": clone_model.account_id,
                    "role_name": clone_model.role_name,
                },
            )
            sentry_sdk.capture_exception()
            self.write_error(500, message="Exception occurred cloning role: " + str(e))
            return

        # if here, role has been successfully cloned
        self.write(results)

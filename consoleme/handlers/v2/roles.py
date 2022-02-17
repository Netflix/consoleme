import base64
import sys
from urllib.parse import parse_qs, urlencode, urlparse

import sentry_sdk
import tornado.escape
import ujson as json
from furl import furl
from pydantic import ValidationError

from consoleme.celery_tasks.celery_tasks import app as celery_app
from consoleme.config import config
from consoleme.handlers.base import BaseAPIV2Handler, BaseMtlsHandler
from consoleme.lib.auth import (
    can_create_roles,
    can_delete_iam_principals,
    can_delete_iam_principals_app,
)
from consoleme.lib.aws import (
    allowed_to_sync_role,
    clone_iam_role,
    create_iam_role,
    delete_iam_role,
)
from consoleme.lib.generic import str2bool
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.v2.aws_principals import get_eligible_role_details, get_role_details
from consoleme.models import (
    CloneRoleRequestModel,
    RoleCreationRequestModel,
    Status2,
    WebResponse,
)

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


class RoleConsoleLoginHandler(BaseAPIV2Handler):
    async def get(self, role=None):
        """
        Attempt to retrieve credentials and redirect the user to the AWS Console
        ---
        description: Retrieves credentials and redirects user to AWS console.
        responses:
            302:
                description: Redirects to AWS console
        """
        arguments = {k: self.get_argument(k) for k in self.request.arguments}
        role = role.lower()
        selected_roles = await group_mapping.filter_eligible_roles(role, self)
        region = arguments.get("r", config.get("aws.region", "us-east-1"))
        redirect = arguments.get("redirect")
        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "role": role,
            "region": region,
            "redirect": redirect,
            "ip": self.ip,
        }

        log_data["role"] = role
        if not selected_roles:
            # Not authorized
            stats.count(
                "RoleConsoleLoginHandler.post",
                tags={
                    "user": self.user,
                    "role": role,
                    "authorized": False,
                    "redirect": bool(redirect),
                },
            )
            log_data[
                "message"
            ] = "You do not have any roles matching your search criteria. "
            log.debug(log_data)
            self.set_status(404)
            self.write({"type": "error", "message": log_data["message"]})
            return

        stats.count(
            "RoleConsoleLoginHandler.post",
            tags={
                "user": self.user,
                "role": role,
                "authorized": True,
                "redirect": bool(redirect),
            },
        )

        if len(selected_roles) > 1:
            # Not sure which role the user wants. Redirect them to main page to select one.
            stats.count(
                "RoleConsoleLoginHandler.post",
                tags={
                    "user": self.user,
                    "role": role,
                    "authorized": False,
                    "redirect": bool(redirect),
                },
            )
            log_data[
                "message"
            ] = "You have more than one role matching your query. Please select one."
            log.debug(log_data)
            warning_message_arg = {
                "warningMessage": base64.b64encode(log_data["message"].encode()).decode(
                    "utf-8"
                )
            }
            redirect_url = furl(f"/?arn={role}")
            redirect_url.args = {
                **redirect_url.args,
                **arguments,
                **warning_message_arg,
            }
            self.write(
                {
                    "type": "redirect",
                    "message": log_data["message"],
                    "reason": "multiple_roles",
                    "redirect_url": redirect_url.url,
                }
            )
            return

        log_data["message"] = "Incoming request"
        log.debug(log_data)

        # User is authorized
        try:
            # User-role logic:
            # User-role should come in as cm-[username or truncated username]_[N or NC]
            user_role = False
            account_id = None

            selected_role = selected_roles[0]

            # User role must be defined as a user attribute
            if (
                self.user_role_name
                and "role/" in selected_role
                and selected_role.split("role/")[1] == self.user_role_name
            ):
                user_role = True
                account_id = selected_role.split("arn:aws:iam::")[1].split(":role")[0]

            url = await aws.generate_url(
                self.user,
                selected_role,
                region,
                user_role=user_role,
                account_id=account_id,
            )
        except Exception as e:
            log_data["message"] = f"Exception generating AWS console URL: {str(e)}"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            stats.count("index.post.exception")
            self.write(
                {
                    "type": "console_url",
                    "message": tornado.escape.xhtml_escape(log_data["message"]),
                    "error": tornado.escape.xhtml_escape(str(log_data["error"])),
                }
            )
            return
        if redirect:
            parsed_url = urlparse(url)
            parsed_url_query = parse_qs(parsed_url.query)
            parsed_url_query["Destination"] = redirect
            updated_query = urlencode(parsed_url_query, doseq=True)
            url = parsed_url._replace(query=updated_query).geturl()
        self.write(
            {
                "type": "redirect",
                "redirect_url": url,
                "reason": "console_login",
                "role": selected_role,
            }
        )
        return


class RolesHandler(BaseAPIV2Handler):
    """Handler for /api/v2/roles

    GET - Allows read access to a list of roles across all accounts. Returned roles are
    limited to what the requesting user has access to.
    POST - Allows (authorized) users to create a role
    """

    allowed_methods = ["GET", "POST"]

    def on_finish(self) -> None:
        if self.request.method != "POST":
            return
        # Force refresh of crednetial authorization mapping after the dynamic config sync period to ensure all workers
        # have the updated configuration
        celery_app.send_task(
            "consoleme.celery_tasks.celery_tasks.cache_policies_table_details",
        )
        celery_app.send_task(
            "consoleme.celery_tasks.celery_tasks.cache_credential_authorization_mapping",
        )

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
        can_create_role = can_create_roles(self.user, self.groups)
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
            log_data["message"] = f"Validation Exception: {str(e)}"
            log_data["error"] = str(e)
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
            log_data["message"] = f"Exception creating role: {str(e)}"
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
        force_refresh = str2bool(
            self.request.arguments.get("force_refresh", [False])[0]
        )

        error = ""

        try:
            role_details = await get_role_details(
                account_id, role_name, extended=True, force_refresh=force_refresh
            )
        except Exception as e:
            sentry_sdk.capture_exception()
            log.error({**log_data, "error": e}, exc_info=True)
            role_details = None
            error = str(e)

        if role_details:
            if not allowed_to_sync_role(role_details.arn, role_details.tags):
                role_details = None

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

        account_id = tornado.escape.xhtml_escape(account_id)
        role_name = tornado.escape.xhtml_escape(role_name)

        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "ip": self.ip,
            "account": account_id,
            "role": role_name,
        }

        can_delete_role = can_delete_iam_principals(self.user, self.groups)
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

    Allows apps to view or delete a role
    """

    allowed_methods = ["DELETE", "GET"]

    def check_xsrf_cookie(self):
        pass

    async def delete(self, account_id, role_name):
        """
        DELETE /api/v2/mtls/roles/{account_id}/{role_name}
        """
        account_id = tornado.escape.xhtml_escape(account_id)
        role_name = tornado.escape.xhtml_escape(role_name)
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
        can_delete_role = can_delete_iam_principals_app(app_name)

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

    async def get(self, account_id, role_name):
        """
        GET /api/v2/mtls/roles/{account_id}/{role_name}
        """
        account_id = tornado.escape.xhtml_escape(account_id)
        role_name = tornado.escape.xhtml_escape(role_name)
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "ip": self.ip,
            "message": "Retrieving role details",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "account_id": account_id,
            "role_name": role_name,
        }
        app_name = self.requester.get("name") or self.requester.get("username")
        stats.count(
            "RoleDetailAppHandler.get",
            tags={
                "requester": app_name,
                "account_id": account_id,
                "role_name": role_name,
            },
        )
        log.debug(log_data)
        force_refresh = str2bool(
            self.request.arguments.get("force_refresh", [False])[0]
        )

        error = ""

        try:
            role_details = await get_role_details(
                account_id, role_name, extended=True, force_refresh=force_refresh
            )
        except Exception as e:
            sentry_sdk.capture_exception()
            log.error({**log_data, "error": e}, exc_info=True)
            role_details = None
            error = str(e)

        if not role_details:
            self.send_error(
                404,
                message=f"Unable to retrieve the specified role: {account_id}/{role_name}. {error}",
            )
            return
        self.write(role_details.json())


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
        can_create_role = can_create_roles(self.user, self.groups)
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


class GetRolesMTLSHandler(BaseMtlsHandler):
    """
    Handler for /api/v2/get_roles
    Consoleme MTLS role handler - returns User's eligible roles and other details about eligible roles
    Pass ?all=true to URL query to return all roles.
    """

    def check_xsrf_cookie(self):
        pass

    def initialize(self):
        self.user: str = None
        self.eligible_roles: list = []

    async def get(self):
        """
        GET /api/v2/get_roles - Endpoint used to get details of eligible roles. Used by weep and newt.
        ---
        get:
            description: Returns a json-encoded list of objects of eligible roles for the user.
            response format: WebResponse. The "data" field within WebResponse is of format EligibleRolesModelArray
            Example response:
                {
                    "status": "success",
                    "status_code": 200,
                    "data": {
                        "roles": [
                                    {
                                        "arn": "arn:aws:iam::123456789012:role/role_name",
                                        "account_id": "123456789012",
                                        "account_friendly_name": "prod",
                                        "role_name": "role_name",
                                        "apps": {
                                            "app_details": [
                                                {
                                                    "name": "consoleme",
                                                    "owner": "owner@example.com",
                                                    "owner_url": null,
                                                    "app_url": "https://example.com"
                                                }
                                            ]
                                        }
                                    },
                                    ...
                                ]
                    }
                }
        """
        self.user: str = self.requester["email"]

        include_all_roles = self.get_arguments("all")
        console_only = True
        if include_all_roles == ["true"]:
            console_only = False

        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": self.user,
            "console_only": console_only,
            "message": "Getting all eligible user roles",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        stats.count("GetRolesMTLSHandler.get", tags={"user": self.user})

        await self.authorization_flow(user=self.user, console_only=console_only)
        eligible_roles_details_array = await get_eligible_role_details(
            sorted(self.eligible_roles)
        )

        res = WebResponse(
            status=Status2.success,
            status_code=200,
            data=eligible_roles_details_array.dict(),
        )
        self.write(res.json(exclude_unset=True))
        await self.finish()

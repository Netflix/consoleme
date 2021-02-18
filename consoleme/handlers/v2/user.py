import sys
from datetime import datetime, timedelta

import pytz
import tornado.web
from email_validator import validate_email

from consoleme.config import config
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.lib.auth import can_admin_all
from consoleme.lib.dynamo import UserDynamoHandler
from consoleme.lib.jwt import generate_jwt_token
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.web import handle_generic_error_response
from consoleme.models import (
    AuthenticationResponse,
    LoginAttemptModel,
    RegistrationAttemptModel,
    UserAuthenticationModel,
    WebResponse,
)

stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
log = config.get_logger()


class UserRegistrationHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.ddb = UserDynamoHandler()

    async def post(self):
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Attempting to register user",
            "user-agent": self.request.headers.get("User-Agent"),
        }

        generic_error_message: str = "User registration failed"
        # Fail if getting users by password is not enabled
        if not config.get("auth.get_user_by_password"):
            errors = [
                "Expected configuration `auth.get_user_by_password`, but it is not enabled."
            ]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "not_configured", log_data
            )
            return
        # Fail if user registration not allowed
        if not config.get("auth.allow_user_registration"):
            errors = [
                "Expected configuration `auth.allow_user_registration`, but it is not enabled."
            ]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "not_configured", log_data
            )
            return

        registration_attempt = RegistrationAttemptModel.parse_raw(self.request.body)
        log_data["username"] = registration_attempt.username
        # Fail if username not valid email address
        if not validate_email(registration_attempt.username):
            errors = ["Username must be a valid e-mail address."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "invalid_request", log_data
            )
            return
        # Fail if user already exists
        if await self.ddb.get_user(registration_attempt.username):
            errors = ["User already exists"]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "invalid_request", log_data
            )
            return

        await self.ddb.create_user(
            registration_attempt.username, registration_attempt.password
        )

        res = WebResponse(
            status="success",
            status_code=200,
            message=f"Successfully created user {registration_attempt.username}.",
        )
        self.write(res.json())


class LoginHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.ddb = UserDynamoHandler()

    def set_default_headers(self) -> None:
        self.set_header("Content-Type", "application/json")

    async def post(self):
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Attempting to authenticate User",
            "user-agent": self.request.headers.get("User-Agent"),
        }
        generic_error_message = "Authentication failed"
        if not config.get("auth.get_user_by_password"):
            errors = [
                "Expected configuration `auth.get_user_by_password`, but it is not enabled."
            ]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "not_configured", log_data
            )
            return
        # Auth cookie must be set to use password authentication.
        if not config.get("auth.set_auth_cookie"):
            errors = [
                "Expected configuration `auth.set_auth_cookie`, but it is not enabled."
            ]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "not_configured", log_data
            )
            return

        login_attempt = LoginAttemptModel.parse_raw(self.request.body)
        log_data["username"] = login_attempt.username
        log_data["after_redirect_uri"] = login_attempt.after_redirect_uri
        authenticated_response: AuthenticationResponse = (
            await self.ddb.authenticate_user(login_attempt)
        )
        if not authenticated_response.authenticated:
            await handle_generic_error_response(
                self,
                generic_error_message,
                authenticated_response.errors,
                403,
                "authentication_failure",
                log_data,
            )
            return
        # Make and set jwt for user
        expiration = datetime.utcnow().replace(tzinfo=pytz.UTC) + timedelta(
            minutes=config.get("jwt.expiration_minutes", 60)
        )
        encoded_cookie = await generate_jwt_token(
            authenticated_response.username,
            authenticated_response.groups,
            exp=expiration,
        )
        self.set_cookie(
            config.get("auth_cookie_name", "consoleme_auth"),
            encoded_cookie,
            expires=expiration,
            secure=config.get(
                "auth.cookie.secure",
                True if "https://" in config.get("url") else False,
            ),
            httponly=config.get("auth.cookie.httponly", True),
            samesite=config.get("auth.cookie.samesite", True),
        )
        res = WebResponse(
            status="redirect",
            redirect_url=login_attempt.after_redirect_uri,
            status_code=200,
            reason="authenticated_redirect",
            message="User has successfully authenticated. Redirecting to their intended destination.",
        )
        self.write(res.json())


class UserManagementHandler(BaseAPIV2Handler):
    def initialize(self):
        self.ddb = UserDynamoHandler()

    async def post(self):
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": self.user,
            "message": "Create/Update User",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "ip": self.ip,
        }
        generic_error_message = "Unable to create/update user"
        log.debug(log_data)
        # Checks authz levels of current user
        if not can_admin_all(self.user, self.groups):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        request = UserAuthenticationModel.parse_raw(self.request.body)
        log_data["requested_user"] = request.username
        if request.action.value == "create":
            log.debug(
                {
                    **log_data,
                    "message": "Creating user",
                    "requested_user": request.username,
                    "requested_groups": request.groups,
                }
            )
            self.ddb.create_user(
                request.username,
                request.password,
                request.groups,
            )
            res = WebResponse(
                status="success",
                status_code=200,
                message=f"Successfully created user {request.username}.",
            )
            self.write(res.json())
            return
        elif request.action.value == "update":
            log.debug(
                {
                    **log_data,
                    "message": "Updating user",
                    "requested_user": request.username,
                    "requested_groups": request.groups,
                }
            )
            self.ddb.update_user(
                request.username,
                request.password,
                request.groups,
            )
            res = WebResponse(
                status="success",
                status_code=200,
                message=f"Successfully updated user {request.username}.",
            )
            self.write(res.json())
            return
        else:
            errors = ["Change type is not supported by this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "invalid_request", log_data
            )
            return

    async def delete(self):
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": self.user,
            "message": "Create/Update User",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "ip": self.ip,
        }
        generic_error_message = "Unable to delete user"
        log.debug(log_data)
        # Checks authz levels of current user
        if not can_admin_all(self.user, self.groups):
            errors = ["User is not authorized to access this endpoint."]

            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return

        request = UserAuthenticationModel.parse_raw(self.request.body)
        log_data["requested_user"] = request.username
        if request.action.value != "delete":
            errors = ["Change type is not supported by this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "invalid_request", log_data
            )
            return

        self.ddb.delete_user(
            request.username,
        )

        log.debug({**log_data, "message": "User successfully deleted"})

import sys
from datetime import datetime, timedelta
from enum import Enum
from typing import List

import pytz
import tornado.web
from consoleme.models import AuthenticationResponse, LoginAttemptModel
from pydantic import BaseModel

from consoleme.config import config
from consoleme.exceptions.exceptions import UnauthorizedToAccess, UnsupportedChangeType
from consoleme.handlers.base import BaseHandler
from consoleme.lib.auth import can_admin_all
from consoleme.lib.dynamo import UserDynamoHandler
from consoleme.lib.jwt import generate_jwt_token
from consoleme.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
log = config.get_logger()


class LoginHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.ddb = UserDynamoHandler()

    async def post(self):
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Attempting to authenticate User",
            "user-agent": self.request.headers.get("User-Agent"),
        }
        login_attempt = LoginAttemptModel.parse_raw(self.request.body)
        log_data["username"] = login_attempt.username
        log_data["after_redirect_uri"] = login_attempt.after_redirect_uri
        authenticated_response: AuthenticationResponse = await self.ddb.authenticate_user(login_attempt)
        if not authenticated_response.authenticated:
            log.error({**log_data, "message": "Authentication failed", "errors": authenticated_response.errors})
            # TODO: Log error - authn failure
            # TODO: return login failure
            return
        # Make and set jwt for user
        if config.get("auth.set_auth_cookie"):
            expiration = datetime.utcnow().replace(tzinfo=pytz.UTC) + timedelta(
                minutes=config.get("jwt.expiration_minutes", 60)
            )
            encoded_cookie = await generate_jwt_token(
                authenticated.email, authenticated.groups, exp=expiration
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
        self.write(
            {
                "type": "redirect",
                "redirect_url": f"{login_attempt.after_redirect_uri}",
                "reason": "authenticated_redirect",
                "message": "User has successfully authenticated. Redirecting to their intended destination.",
            }
        )


# TODO: figure out how to add and remove groups from users. In the future we can sync
class User(BaseHandler):
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
        log.debug(log_data)
        # Checks authz levels of current user
        if not can_admin_all(self.user, self.groups):
            log.error(
                {
                    **log_data,
                    "message": "User is not authorized to access this endpoint.",
                }
            )
            raise UnauthorizedToAccess("You not authorized to administer users.")
        request = UserModel.parse_raw(self.request.body)
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
            # TODO: Talk to Hee Won about a standard way to return errors that we can surface to end-users
            self.ddb.create_user(
                request.username,
                request.password,
                request.groups,
            )
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
        else:
            log.error(
                {
                    **log_data,
                    "message": "Change type is not supported by this endpoint.",
                }
            )
            raise UnsupportedChangeType(
                "Change type is not supported by this endpoint."
            )

    async def delete(self):
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": self.user,
            "message": "Create/Update User",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "ip": self.ip,
        }
        log.debug(log_data)
        # Checks authz levels of current user
        if not can_admin_all(self.user, self.groups):
            log.error(
                {
                    **log_data,
                    "message": "User is not authorized to access this endpoint.",
                }
            )
            raise UnauthorizedToAccess("You not authorized to administer users.")

        request = UserModel.parse_raw(self.request.body)
        log_data["requested_user"] = request.username
        if request.action.value != "delete":
            log.error(
                {
                    **log_data,
                    "message": "Change type is not supported by this endpoint.",
                }
            )
            raise UnsupportedChangeType(
                "Change type is not supported by this endpoint."
            )

        self.ddb.delete_user(
            request.username,
        )

        log.debug({**log_data, "message": "User successfully deleted"})

"""Handle the base."""
import traceback

import redis
import tornado.httpclient
import tornado.httputil
import tornado.web
import ujson as json
import uuid
from asgiref.sync import sync_to_async
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from raven.contrib.tornado import SentryMixin
from tornado import httputil
from typing import Any, Union

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    InvalidCertificateException,
    MissingCertificateException,
    NoGroupsException,
    NoUserException,
)
from consoleme.exceptions.exceptions import WebAuthNError
from consoleme.lib.alb_auth import authenticate_user_by_alb_auth
from consoleme.lib.auth import AuthenticationError
from consoleme.lib.generic import render_404
from consoleme.lib.jwt import validate_and_return_jwt_token, generate_jwt_token
from consoleme.lib.oauth2 import authenticate_user_by_oauth2
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.redis import RedisHandler
from consoleme.lib.saml import authenticate_user_by_saml

log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics"))()
auth = get_plugin_by_name(config.get("plugins.auth"))()


class BaseJSONHandler(SentryMixin, tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        self.jwt_validator = kwargs.pop("jwt_validator", None)
        self.auth_required = kwargs.pop("auth_required", True)
        if self.jwt_validator is None:
            raise TypeError("Missing required keyword arg jwt_validator")
        super().__init__(*args, **kwargs)

    def check_xsrf_cookie(self):
        # CSRF token is not needed since this is protected by raw OAuth2 tokens
        pass

    def options(self, *args):
        self.set_header(
            "Access-Control-Allow-Headers",
            self.request.headers["Access-Control-Request-Headers"],
        )
        self.set_header("Content-Length", "0")
        self.set_status(204)
        self.finish()

    def prepare(self):
        stats.timer("base_handler.incoming_request")
        if self.request.method.lower() == "options":
            return
        payload = self.get_current_user()
        self.auth_context = payload
        self.user = payload["email"]

    def set_default_headers(self, *args, **kwargs):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header(
            "Access-Control-Allow-Methods", "GET,HEAD,PUT,PATCH,POST,DELETE"
        )
        self.set_header("Access-Control-Allow-Credentials", "true")
        self.set_header("Content-Type", "application/json")

    def write_error(self, status_code, **kwargs):
        self.set_header("Content-Type", "application/problem+json")
        kwargs.get("message")
        self.finish(
            json.dumps(
                {
                    "status": status_code,
                    "title": httputil.responses.get(status_code, "Unknown"),
                    "message": kwargs.get("message", self._reason),
                }
            )
        )

    def get_current_user(self):
        try:
            if config.get("development") and config.get("json_authentication_override"):
                return config.get("json_authentication_override.email")
            tkn_header = self.request.headers["authorization"]
        except KeyError:
            raise WebAuthNError(reason="Missing Authorization Header")
        else:
            tkn_str = tkn_header.split(" ")[-1]
        try:
            tkn = self.jwt_validator(tkn_str)
        except AuthenticationError as e:
            raise WebAuthNError(reason=e.message)
        else:
            return tkn


class BaseHandler(SentryMixin, tornado.web.RequestHandler):
    """Default BaseHandler."""

    def write_error(self, status_code: int, **kwargs: Any) -> None:
        if self.settings.get("serve_traceback") and "exc_info" in kwargs:
            # in debug mode, try to send a traceback
            self.set_header("Content-Type", "text/plain")
            for line in traceback.format_exception(*kwargs["exc_info"]):
                self.write(line)
            self.finish()
        else:
            if status_code == 404:
                render_404(self, config)
                return
            else:
                self.finish(
                    "<html><title>%(code)d: %(message)s</title>"
                    "<body>%(code)d: %(message)s</body></html>"
                    % {
                        "code": status_code,
                        "message": f"{self._reason} - {config.get('errors.custom_website_error_message', '')}",
                    }
                )

    def data_received(self, chunk):
        """Receives the data."""
        pass

    def set_default_headers(self) -> None:
        self.set_header(
            "Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"
        )

    async def prepare(self) -> None:
        if config.get("tornado.xsrf", True):
            self.set_cookie(config.get("xsrf_cookie_name", "_xsrf"), self.xsrf_token)
        self.responses = []
        self.request_uuid = str(uuid.uuid4())
        stats.timer("base_handler.incoming_request")
        return await self.authorization_flow()

    def write(self, chunk: Union[str, bytes, dict]) -> None:
        if config.get("_security_risk_full_debugging.enabled"):
            self.responses.append(chunk)
        super(BaseHandler, self).write(chunk)

    def on_finish(self) -> None:
        if config.get("_security_risk_full_debugging.enabled"):
            request_details = {
                "path": self.request.path,
                "method": self.request.method,
                "body": self.request.body,
                "arguments": self.request.arguments,
                "body_arguments": self.request.body_arguments,
                "headers": dict(self.request.headers.items()),
                "query": self.request.query,
                "query_arguments": self.request.query_arguments,
                "uri": self.request.uri,
                "cookies": dict(self.request.cookies.items()),
                "response": self.responses,
            }
            with open(config.get("_security_risk_full_debugging.file"), "a+") as f:
                f.write(json.dumps(request_details))

    async def authorization_flow(
        self, user: str = None, console_only: bool = True, refresh_cache: bool = False
    ) -> None:
        """Perform high level authorization flow."""
        self.request_uuid = str(uuid.uuid4())
        refresh_cache = (
            self.request.arguments.get("refresh_cache", [False])[0] or refresh_cache
        )
        if not refresh_cache and config.get(
            "dynamic_config.role_cache.always_refresh_roles_cache", False
        ):
            refresh_cache = True

        self.red = await RedisHandler().redis()

        # Load auth plugin
        auth = get_plugin_by_name(config.get("plugins.auth"))()
        group_mapping = get_plugin_by_name(config.get("plugins.group_mapping"))()

        self.ip = self.request.headers.get(
            "X-Forwarded-For", self.request.remote_ip
        ).split(",")[0]
        self.user = user
        self.groups = None
        self.user_role_name = None
        self.legacy_user_role_mapping = {}

        log_data = {
            "function": "Basehandler.authorization_flow",
            "ip": self.ip,
            "request_path": self.request.uri,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "message": "Incoming request",
        }

        log.debug(log_data)

        # Check to see if user has a valid auth cookie
        if config.get("auth_cookie_name"):
            auth_cookie = self.get_cookie(config.get("auth_cookie_name"))
            if auth_cookie:
                res = await validate_and_return_jwt_token(auth_cookie)
                if res and isinstance(res, dict):
                    self.user = res.get("user")
                    self.groups = res.get("groups")

        if not self.user:
            # SAML flow. If user has a JWT signed by ConsoleMe, and SAML is enabled in configuration, user will go
            # through this flow.

            if config.get("auth.get_user_by_saml"):
                res = await authenticate_user_by_saml(self)
                if not res:
                    return

        if not self.user:
            if config.get("auth.get_user_by_oidc"):
                res = await authenticate_user_by_oauth2(self)
                if not res:
                    return
                if res and isinstance(res, dict):
                    self.user = res.get("user")
                    self.groups = res.get("groups")

        if not self.user:
            if config.get("auth.get_user_by_aws_alb_auth"):
                res = await authenticate_user_by_alb_auth(self)
                if not res:
                    return
                if res and isinstance(res, dict):
                    self.user = res.get("user")
                    self.groups = res.get("groups")

        if not self.user:
            try:
                # Get user. Config options can specify getting username from headers or
                # oauth, but custom plugins are also allowed to override this.
                self.user = await auth.get_user(headers=self.request.headers)
                if not self.user:
                    raise NoUserException(
                        f"User not detected. Headers: {self.request.headers}"
                    )
                log_data["user"] = self.user
            except NoUserException:
                self.clear()
                self.set_status(403)
                stats.count(
                    "Basehandler.authorization_flow.no_user_detected",
                    tags={
                        "request_path": self.request.uri,
                        "ip": self.ip,
                        "user_agent": self.request.headers.get("User-Agent"),
                    },
                )
                log_data["message"] = "No user detected. Check configuration."
                log.error(log_data)
                await self.finish(log_data["message"])
                raise

        self.contractor = await auth.is_user_contractor(self.user)

        if not refresh_cache:
            try:
                cache_r = self.red.get(f"USER-{self.user}-CONSOLE-{console_only}")
            except redis.exceptions.ConnectionError:
                cache_r = None
            if cache_r:
                log_data["message"] = "Loading from cache"
                log.debug(log_data)
                cache = json.loads(cache_r)
                self.groups = cache.get("groups")
                self.eligible_roles = cache.get("eligible_roles")
                self.eligible_accounts = cache.get("eligible_accounts")
                self.user_role_name = cache.get("user_role_name")
                self.legacy_user_role_mapping = cache.get("legacy_user_role_mapping")
                return

        try:
            if not self.groups:
                self.groups = await auth.get_groups(
                    self.user, headers=self.request.headers
                )
            if not self.groups:
                raise NoGroupsException(
                    f"Groups not detected. Headers: {self.request.headers}"
                )

        except NoGroupsException:
            self.clear()
            self.set_status(403)
            stats.count("Basehandler.authorization_flow.no_groups_detected")
            log_data["message"] = "No groups detected. Check configuration."
            log.error(log_data)
            await self.finish(log_data["message"])
            return

        # Set User Role Name

        if (
            config.get("user_roles.opt_in_group")
            and config.get("user_roles.opt_in_group") in self.groups
        ):
            # Get or create user_role_name attribute
            self.user_role_name = await auth.get_or_create_user_role_name(self.user)

        self.eligible_roles = await group_mapping.get_eligible_roles(
            self.user,
            self.groups,
            self.user_role_name,
            legacy_mapping=self.legacy_user_role_mapping,
            console_only=console_only,
        )

        if not self.eligible_roles:
            log_data[
                "message"
            ] = "No eligible roles detected for user. But letting them continue"
            log.error(log_data)
        log_data["eligible_roles"] = len(self.eligible_roles)

        try:
            self.eligible_accounts = await group_mapping.get_eligible_accounts(
                self.eligible_roles
            )
            log_data["eligible_accounts"] = self.eligible_accounts
            log_data["message"] = "Successfully authorized user."
            log.debug(log_data)
        except Exception:
            stats.count("Basehandler.authorization_flow.exception")
            log.error(log_data, exc_info=True)
            raise
        if self.groups and config.get("dynamic_config.role_cache.cache_roles", True):
            try:
                self.red.setex(
                    f"USER-{self.user}-CONSOLE-{console_only}",
                    config.get("dynamic_config.role_cache.cache_expiration", 500),
                    json.dumps(
                        {
                            "groups": self.groups,
                            "eligible_roles": self.eligible_roles,
                            "eligible_accounts": self.eligible_accounts,
                            "user_role_name": self.user_role_name,
                            "legacy_user_role_mapping": self.legacy_user_role_mapping,
                        }
                    ),
                )
            except redis.exceptions.ConnectionError:
                pass
        if (
            config.get("auth.set_auth_cookie")
            and config.get("auth_cookie_name")
            and not self.get_cookie(config.get("auth_cookie_name"))
        ):
            encoded_cookie = await generate_jwt_token(self.user, self.groups)
            self.set_cookie(config.get("auth_cookie_name"), encoded_cookie)

    async def prepare_tornado_request_for_saml(self):
        dataDict = {}

        for key in self.request.arguments:
            dataDict[key] = self.request.arguments[key][0].decode("utf-8")

        result = {
            "https": "on" if self.request == "https" else "off",
            "http_host": tornado.httputil.split_host_and_port(self.request.host)[0],
            "script_name": self.request.path,
            "server_port": tornado.httputil.split_host_and_port(self.request.host)[1],
            "get_data": dataDict,
            "post_data": dataDict,
            "query_string": self.request.query,
        }
        return result

    @staticmethod
    async def init_saml_auth(req):
        auth = await sync_to_async(OneLogin_Saml2_Auth)(
            req, custom_base_path=config.get("get_user_by_saml_settings.saml_path")
        )
        return auth


class BaseMtlsHandler(BaseHandler):
    def initialize(self, **kwargs):
        self.kwargs = kwargs

    async def prepare(self):
        self.responses = []
        self.request_uuid = str(uuid.uuid4())
        stats.timer("base_handler.incoming_request")
        try:
            await auth.validate_certificate(self.request.headers)
        except InvalidCertificateException:
            stats.count("GetCredentialsHandler.post.invalid_certificate_header_value")
            self.set_status(403)
            self.write({"code": "403", "message": "Invalid Certificate"})
            await self.finish()
            return

        # Extract user from valid certificate
        try:
            self.requester = await auth.extract_user_from_certificate(
                self.request.headers
            )
        except (MissingCertificateException, Exception) as e:
            if isinstance(e, MissingCertificateException):
                stats.count("GetCredentialsHandler.post.missing_certificate_header")
                message = "Missing Certificate in Header."
            else:
                stats.count("GetCredentialsHandler.post.invalid_mtls_certificate")
                message = "Invalid Mtls Certificate."
            self.set_status(400)
            self.write({"code": "400", "message": message})
            await self.finish()
            return
        self.ip = self.request.headers.get(
            "X-Forwarded-For", self.request.remote_ip
        ).split(",")[0]
        self.current_cert_age = await auth.get_cert_age_seconds(self.request.headers)

    def write(self, chunk: Union[str, bytes, dict]) -> None:
        if config.get("_security_risk_full_debugging.enabled"):
            self.responses.append(chunk)
        super(BaseMtlsHandler, self).write(chunk)

    def on_finish(self) -> None:
        if config.get("_security_risk_full_debugging.enabled"):
            request_details = {
                "path": self.request.path,
                "method": self.request.method,
                "body": self.request.body,
                "arguments": self.request.arguments,
                "body_arguments": self.request.body_arguments,
                "headers": dict(self.request.headers.items()),
                "query": self.request.query,
                "query_arguments": self.request.query_arguments,
                "uri": self.request.uri,
                "cookies": dict(self.request.cookies.items()),
                "response": self.responses,
            }
            with open(config.get("_security_risk_full_debugging.file"), "a+") as f:
                f.write(json.dumps(request_details))


class NoCacheStaticFileHandler(tornado.web.StaticFileHandler):
    def set_default_headers(self) -> None:
        self.set_header(
            "Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"
        )

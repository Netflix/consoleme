"""Handle the base."""
import asyncio
import traceback
import uuid
from typing import Any, Union

import redis
import tornado.httpclient
import tornado.httputil
import tornado.web
import ujson as json
from asgiref.sync import sync_to_async
from tornado import httputil

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    InvalidCertificateException,
    MissingCertificateException,
    NoGroupsException,
    NoUserException,
    WebAuthNError,
)
from consoleme.lib.alb_auth import authenticate_user_by_alb_auth
from consoleme.lib.auth import AuthenticationError
from consoleme.lib.generic import render_404
from consoleme.lib.jwt import generate_jwt_token, validate_and_return_jwt_token
from consoleme.lib.oauth2 import authenticate_user_by_oauth2
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.redis import RedisHandler
from consoleme.lib.saml import authenticate_user_by_saml
from consoleme.lib.tracing import ConsoleMeTracer

if config.get("auth.get_user_by_saml"):
    from onelogin.saml2.auth import OneLogin_Saml2_Auth

log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics"))()
auth = get_plugin_by_name(config.get("plugins.auth"))()
group_mapping = get_plugin_by_name(config.get("plugins.group_mapping"))()


class BaseJSONHandler(tornado.web.RequestHandler):
    # These methods are returned in OPTIONS requests.
    # Default methods can be overridden by setting this variable in child classes.
    allowed_methods = ["GET", "HEAD", "PUT", "PATCH", "POST", "DELETE"]

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

    async def prepare(self):
        stats.timer("base_handler.incoming_request")
        if self.request.method.lower() == "options":
            return
        self.request_uuid = str(uuid.uuid4())
        payload = self.get_current_user()
        self.auth_context = payload
        self.user = payload["email"]

    def set_default_headers(self, *args, **kwargs):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", ",".join(self.allowed_methods))
        self.set_header("Access-Control-Allow-Credentials", "true")
        self.set_header("Content-Type", "application/json")

    def write_error(self, status_code, **kwargs):
        self.set_header("Content-Type", "application/problem+json")
        title = httputil.responses.get(status_code, "Unknown")
        message = kwargs.get("message", self._reason)
        # self.set_status() modifies self._reason, so this call should come after we grab the reason
        self.set_status(status_code)
        self.finish(
            json.dumps(
                {"status": status_code, "title": title, "message": message}
            )  # noqa
        )

    def get_current_user(self):
        try:
            if config.get("development") and config.get("json_authentication_override"):
                return config.get("json_authentication_override")
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


class BaseHandler(tornado.web.RequestHandler):
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

    def initialize(self) -> None:
        self.tracer = None
        self.responses = []
        super(BaseHandler, self).initialize()

    async def prepare(self) -> None:
        self.tracer = None
        await self.configure_tracing()

        if config.get("tornado.xsrf", True):
            cookie_kwargs = config.get("tornado.xsrf_cookie_kwargs", {})
            self.set_cookie(
                config.get("xsrf_cookie_name", "_xsrf"),
                self.xsrf_token,
                **cookie_kwargs,
            )
        self.request_uuid = str(uuid.uuid4())
        stats.timer("base_handler.incoming_request")
        return await self.authorization_flow()

    def write(self, chunk: Union[str, bytes, dict]) -> None:
        if config.get("_security_risk_full_debugging.enabled"):
            if not hasattr(self, "responses"):
                self.responses = []
            self.responses.append(chunk)
        super(BaseHandler, self).write(chunk)

    async def configure_tracing(self):
        self.tracer = ConsoleMeTracer()
        primary_span_name = "{0} {1}".format(
            self.request.method.upper(), self.request.path
        )
        tracer_tags = {
            "http.host": config.hostname,
            "http.method": self.request.method.upper(),
            "http.path": self.request.path,
            "ca": self.request.headers.get(
                "X-Forwarded-For", self.request.remote_ip
            ).split(",")[
                0
            ],  # Client IP
            "http.url": self.request.full_url(),
        }
        tracer = await self.tracer.configure_tracing(
            primary_span_name, tags=tracer_tags
        )
        if tracer:
            for k, v in tracer.headers.items():
                self.set_header(k, v)

    def on_finish(self) -> None:
        if hasattr(self, "tracer"):
            asyncio.ensure_future(
                self.tracer.set_additional_tags({"http.status_code": self.get_status()})
            )
            asyncio.ensure_future(self.tracer.finish_spans())
            asyncio.ensure_future(self.tracer.disable_tracing())

        if config.get("_security_risk_full_debugging.enabled"):
            responses = None
            if hasattr(self, "responses"):
                responses = self.responses
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
                "response": responses,
            }
            with open(config.get("_security_risk_full_debugging.file"), "a+") as f:
                f.write(json.dumps(request_details))
        super(BaseHandler, self).on_finish()

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
        self.ip = self.request.headers.get(
            "X-Forwarded-For", self.request.remote_ip
        ).split(",")[0]
        self.user = user
        self.groups = None
        self.user_role_name = None

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
            # Check for development mode and a configuration override that specify the user and their groups.
            if config.get("development") and config.get("_development_user_override"):
                self.user = config.get("_development_user_override")
            if config.get("development") and config.get("_development_groups_override"):
                self.groups = config.get("_development_groups_override")

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
            self.user, self.groups, self.user_role_name, console_only=console_only
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
        if self.tracer:
            await self.tracer.set_additional_tags({"USER": self.user})

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


class BaseAPIV1Handler(BaseHandler):
    """Default API Handler for api/v1/* routes."""

    def set_default_headers(self) -> None:
        self.set_header("Content-Type", "application/json")


class BaseAPIV2Handler(BaseHandler):
    """Default API Handler for api/v2/* routes."""

    def set_default_headers(self) -> None:
        self.set_header("Content-Type", "application/json")

    def write_error(self, status_code: int, **kwargs: Any) -> None:
        if self.settings.get("serve_traceback") and "exc_info" in kwargs:
            # in debug mode, try to send a traceback
            self.set_header("Content-Type", "text/plain")
            self.set_status(status_code)
            for line in traceback.format_exception(*kwargs["exc_info"]):
                self.write(line)
            self.finish()
        else:
            self.set_header("Content-Type", "application/problem+json")
            title = httputil.responses.get(status_code, "Unknown")
            message = kwargs.get("message", self._reason)
            # self.set_status() modifies self._reason, so this call should come after we grab the reason
            self.set_status(status_code)
            self.finish(
                json.dumps(
                    {"status": status_code, "title": title, "message": message}
                )  # noqa
            )


class BaseMtlsHandler(BaseAPIV2Handler):
    def initialize(self, **kwargs):
        self.kwargs = kwargs

    async def prepare(self):
        self.tracer = None
        self.span = None
        self.spans = {}
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
        await self.configure_tracing()

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
        super(BaseMtlsHandler, self).on_finish()


class NoCacheStaticFileHandler(tornado.web.StaticFileHandler):
    def set_default_headers(self) -> None:
        self.set_header(
            "Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"
        )

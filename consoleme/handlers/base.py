"""Handle the base."""
import traceback
import uuid
from typing import Any

import jwt
import redis
import tornado.httputil
import tornado.web
import ujson as json
from asgiref.sync import sync_to_async
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.errors import OneLogin_Saml2_Error
from raven.contrib.tornado import SentryMixin
from tornado import httputil

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    InvalidCertificateException,
    MissingCertificateException,
    NoGroupsException,
    NoUserException,
)
from consoleme.lib.auth import AuthenticationError
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.redis import RedisHandler

log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics"))()
auth = get_plugin_by_name(config.get("plugins.auth"))()


class WebAuthNError(tornado.web.HTTPError):
    """Authentication Error"""

    def __init__(self, **kwargs):
        kwargs["status_code"] = 401
        super().__init__(**kwargs)


class NotFoundError(tornado.web.HTTPError):
    """Not Found Error"""

    def __init__(self, **kwargs):
        kwargs["status_code"] = 404
        super().__init__(**kwargs)


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
        self.request_uuid = str(uuid.uuid4())
        stats.timer("base_handler.incoming_request")
        return await self.authorization_flow()

    async def authorization_flow(
        self, user: str = None, console_only: bool = True, refresh_cache: bool = False
    ) -> None:
        """Perform high level authorization flow."""
        self.request_uuid = str(uuid.uuid4())
        # TODO(ccastrapel): For OSS plugin, Take user's SAML Role Assertions and determine
        # eligible AWS roles from those

        # TODO(ccastrapel): Separate out accessui and other handlers into internal plugin,
        # figure out how to fix the routing on these.
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
        decoded_jwt = None

        log_data = {
            "function": "Basehandler.authorization_flow",
            "ip": self.ip,
            "request_path": self.request.uri,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "message": "Incoming request",
        }

        log.debug(log_data)

        if not self.user:
            # SAML flow. If user has a JWT signed by ConsoleMe, and SAML is enabled in configuration, user will go
            # through this flow.

            if config.get("auth.get_user_by_saml"):
                saml_jwt_secret = config.get("saml_jwt_secret")
                if not saml_jwt_secret:
                    raise Exception("'saml_jwt_secret' configuration value is not set.")
                # Get secure cookie here
                auth_cookie = self.get_cookie("consoleme_auth")

                if auth_cookie:
                    try:
                        decoded_jwt = jwt.decode(
                            auth_cookie, saml_jwt_secret, algorithm="HS256"
                        )
                        user_list = decoded_jwt.get("samlUserdata", {}).get(
                            config.get(
                                "get_user_by_saml_settings.jwt.email_key", "email"
                            ),
                            [],
                        )
                        if len(user_list) > 0:
                            self.user = user_list[0]
                        self.groups = decoded_jwt.get("samlUserdata", {}).get(
                            config.get(
                                "get_user_by_saml_settings.jwt.groups_key", "groups"
                            ),
                            [],
                        )
                    except jwt.ExpiredSignatureError:
                        # Force user to reauth.
                        pass
                if not decoded_jwt:
                    saml_req = await self.prepare_tornado_request_for_saml()
                    auth = await self.init_saml_auth(saml_req)
                    try:
                        await sync_to_async(auth.process_response)()
                    except OneLogin_Saml2_Error:
                        return self.redirect(auth.login())

                    await sync_to_async(auth.get_errors)()
                    not_auth_warn = not await sync_to_async(auth.is_authenticated)()
                    if not_auth_warn:
                        return self.redirect(auth.login())

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
                message = "Invalid Mtld Certificate."
            self.set_status(400)
            self.write({"code": "400", "message": message})
            await self.finish()
            return
        self.ip = self.request.headers.get(
            "X-Forwarded-For", self.request.remote_ip
        ).split(",")[0]
        self.current_cert_age = await auth.get_cert_age_seconds(self.request.headers)


class NoCacheStaticFileHandler(tornado.web.StaticFileHandler):
    def set_default_headers(self) -> None:
        self.set_header(
            "Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"
        )

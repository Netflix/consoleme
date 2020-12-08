"""Web routes."""
import os

import pkg_resources
import requests
import sentry_sdk
import tornado.autoreload
import tornado.web
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.tornado import TornadoIntegration

import consoleme
from consoleme.config import config
from consoleme.handlers.auth import AuthHandler
from consoleme.handlers.v1.credentials import GetCredentialsHandler
from consoleme.handlers.v1.headers import ApiHeaderHandler, HeaderHandler
from consoleme.handlers.v1.health import HealthHandler
from consoleme.handlers.v1.policies import (
    ApiResourceTypeAheadHandler,
    AutocompleteHandler,
    ResourceTypeAheadHandler,
)
from consoleme.handlers.v1.roles import GetRolesHandler
from consoleme.handlers.v1.saml import SamlHandler
from consoleme.handlers.v2.challenge import (
    ChallengeGeneratorHandler,
    ChallengePollerHandler,
    ChallengeValidatorHandler,
)
from consoleme.handlers.v2.dynamic_config import DynamicConfigApiHandler
from consoleme.handlers.v2.errors import NotFoundHandler as V2NotFoundHandler
from consoleme.handlers.v2.generate_changes import GenerateChangesHandler
from consoleme.handlers.v2.generate_policy import GeneratePolicyHandler
from consoleme.handlers.v2.index import (
    EligibleRoleHandler,
    EligibleRolePageConfigHandler,
    FrontendHandler,
)
from consoleme.handlers.v2.policies import (
    ManagedPoliciesHandler,
    PoliciesHandler,
    PoliciesPageConfigHandler,
)
from consoleme.handlers.v2.requests import (
    RequestDetailHandler,
    RequestHandler,
    RequestsHandler,
    RequestsPageConfigHandler,
)
from consoleme.handlers.v2.resources import ResourceDetailHandler
from consoleme.handlers.v2.roles import (
    AccountRolesHandler,
    RoleCloneHandler,
    RoleConsoleLoginHandler,
    RoleDetailAppHandler,
    RoleDetailHandler,
    RolesHandler,
)
from consoleme.handlers.v2.self_service import SelfServiceConfigHandler
from consoleme.handlers.v2.typeahead import ResourceTypeAheadHandlerV2
from consoleme.handlers.v2.user_profile import UserProfileHandler
from consoleme.lib.auth import mk_jwks_validator
from consoleme.lib.plugins import get_plugin_by_name

internal_routes = get_plugin_by_name(config.get("plugins.internal_routes"))()

log = config.get_logger()


def make_jwt_validator():
    jwk_url = config.get("sso.jwk_url")
    if not jwk_url:
        raise Exception("Config 'sso.jwk_url' is not defined")
    jwk_set = requests.get(jwk_url).json()
    keys = [k for k in jwk_set["keys"] if k["kty"] == "RSA"]
    jwk_schema = config.get("sso.jwk_schema")
    if not jwk_schema:
        raise Exception("Config 'sso.jwk_schema' is not defined")
    return mk_jwks_validator(keys, jwk_schema["header"], jwk_schema["payload"])


def make_app(jwt_validator=None):
    """make_app."""
    path = pkg_resources.resource_filename("consoleme", "templates")

    oss_routes = [
        (r"/auth", AuthHandler),
        (r"/healthcheck", HealthHandler),
        (
            r"/static/(.*)",
            tornado.web.StaticFileHandler,
            dict(path=os.path.join(path, "static")),
        ),
        (
            r"/images/(.*)",
            tornado.web.StaticFileHandler,
            dict(path=os.path.join(path, "images")),
        ),
        (
            r"/(favicon.ico)",
            tornado.web.StaticFileHandler,
            dict(path=os.path.join(path, "static")),
        ),
        (r"/api/v1/get_credentials", GetCredentialsHandler),
        (r"/api/v1/get_roles", GetRolesHandler),
        # Used to autocomplete AWS permissions
        (r"/api/v1/policyuniverse/autocomplete/?", AutocompleteHandler),
        (r"/api/v2/user_profile/?", UserProfileHandler),
        (r"/api/v2/self_service_config/?", SelfServiceConfigHandler),
        (r"/api/v1/myheaders/?", ApiHeaderHandler),
        (r"/api/v1/policies/typeahead", ApiResourceTypeAheadHandler),
        (r"/api/v2/dynamic_config", DynamicConfigApiHandler),
        (r"/api/v2/eligible_roles", EligibleRoleHandler),
        (r"/api/v2/eligible_roles_page_config", EligibleRolePageConfigHandler),
        (r"/api/v2/policies_page_config", PoliciesPageConfigHandler),
        (r"/api/v2/requests_page_config", RequestsPageConfigHandler),
        (r"/api/v2/generate_policy", GeneratePolicyHandler),
        (r"/api/v2/managed_policies/(\d{12})", ManagedPoliciesHandler),
        (r"/api/v2/policies", PoliciesHandler),
        (r"/api/v2/request", RequestHandler),
        (r"/api/v2/requests", RequestsHandler),
        (r"/api/v2/requests/([a-zA-Z0-9_-]+)", RequestDetailHandler),
        (r"/api/v2/roles/?", RolesHandler),
        (r"/api/v2/roles/(\d{12})", AccountRolesHandler),
        (r"/api/v2/roles/(\d{12})/(.*)", RoleDetailHandler),
        (
            r"/api/v2/resources/(\d{12})/(s3|sqs|sns)(?:/([a-z\-1-9]+))?/(.*)",
            ResourceDetailHandler,
        ),
        (r"/api/v2/mtls/roles/(\d{12})/(.*)", RoleDetailAppHandler),
        (r"/api/v2/clone/role", RoleCloneHandler),
        (r"/api/v2/generate_changes/?", GenerateChangesHandler),
        (r"/api/v2/typeahead/resources", ResourceTypeAheadHandlerV2),
        (r"/api/v2/role_login/(.*)", RoleConsoleLoginHandler),
        (r"/myheaders/?", HeaderHandler),
        (r"/policies/typeahead/?", ResourceTypeAheadHandler),
        (r"/saml/(.*)", SamlHandler),
        (
            r"/api/v2/challenge_validator/([a-zA-Z0-9_-]+)",
            ChallengeValidatorHandler,
            {"type": "api"},
        ),
        (r"/noauth/v1/challenge_generator/(.*)", ChallengeGeneratorHandler),
        (r"/noauth/v1/challenge_poller/([a-zA-Z0-9_-]+)", ChallengePollerHandler),
        (r"/api/v2/.*", V2NotFoundHandler),
        (
            r"/(.*)",
            FrontendHandler,
            dict(path=path, default_filename="index.html"),
        ),
    ]

    # Prioritize internal routes before OSS routes so that OSS routes can be overrided if desired.
    internal_route_list = internal_routes.get_internal_routes(
        make_jwt_validator, jwt_validator
    )
    routes = internal_route_list + oss_routes

    app = tornado.web.Application(
        routes,
        debug=config.get("tornado.debug", False),
        xsrf_cookies=config.get("tornado.xsrf", True),
        xsrf_cookie_kwargs=config.get("tornado.xsrf_cookie_kwargs", {}),
        template_path=config.get(
            "tornado.template_path", f"{os.path.dirname(consoleme.__file__)}/templates"
        ),
        ui_modules=internal_routes.ui_modules,
    )
    sentry_dsn = config.get("sentry.dsn")

    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[
                TornadoIntegration(),
                AioHttpIntegration(),
                RedisIntegration(),
            ],
        )

    return app

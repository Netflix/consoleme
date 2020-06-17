"""Web routes."""
import os
import sys

import pkg_resources
import requests
import tornado.autoreload
import tornado.web
from apispec import APISpec
from apispec.exceptions import APISpecError
from apispec_webframeworks.tornado import TornadoPlugin
from raven.contrib.tornado import AsyncSentryClient

import consoleme
from consoleme.config import config
from consoleme.handlers.auth import AuthHandler
from consoleme.handlers.base import NoCacheStaticFileHandler
from consoleme.handlers.v1.autologin import AutoLoginHandler
from consoleme.handlers.v1.credentials import GetCredentialsHandler
from consoleme.handlers.v1.dynamic_config import DynamicConfigHandler
from consoleme.handlers.v1.errors import Consolme404Handler
from consoleme.handlers.v1.headers import (
    ApiHeaderHandler,
    HeaderHandler,
    SiteConfigHandler,
    UserProfileHandler,
)
from consoleme.handlers.v1.health import HealthHandler
from consoleme.handlers.v1.index import IndexHandler

# from consoleme.handlers.v1.index import IndexHandler
from consoleme.handlers.v1.policies import (
    ApiResourceTypeAheadHandler,
    AutocompleteHandler,
    GetPoliciesHandler,
    PolicyEditHandler,
    PolicyReviewHandler,
    PolicyReviewSubmitHandler,
    PolicyViewHandler,
    ResourcePolicyEditHandler,
    ResourceTypeAheadHandler,
    SelfServiceHandler,
    SelfServiceNewHandler,
)
from consoleme.handlers.v1.roles import GetRolesHandler
from consoleme.handlers.v1.saml import SamlHandler
from consoleme.handlers.v1.swagger import SwaggerHandler, SwaggerJsonGenerator
from consoleme.handlers.v2.errors import NotFoundHandler as V2NotFoundHandler
from consoleme.handlers.v2.generate_changes import GenerateChangesHandler
from consoleme.handlers.v2.generate_policy import GeneratePolicyHandler

# Todo: UIREFACTOR: Remove reference to /v2 when new UI is complete
from consoleme.handlers.v2.index import IndexHandler as IndexHandlerV2  # noqa
from consoleme.handlers.v2.requests import RequestDetailHandler, RequestsHandler
from consoleme.handlers.v2.roles import (
    AccountRolesHandler,
    RoleCloneHandler,
    RoleDetailAppHandler,
    RoleDetailHandler,
    RolesHandler,
)
from consoleme.lib.auth import mk_jwks_validator
from consoleme.lib.plugins import get_plugin_by_name

internal_routes = get_plugin_by_name(config.get("plugins.internal_routes"))()

spec = APISpec(
    title="Consoleme",
    version="1.0.0",
    openapi_version="3.0.2",
    plugins=[TornadoPlugin()],
    info=dict(description="Access to AWS Console and Google Groups"),
)

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

    routes = [
        (r"/", IndexHandler),
        (r"/selfservice", IndexHandler),
        (r"/login", IndexHandler),
        (r"/auth", AuthHandler),
        (r"/role/(.*)", AutoLoginHandler),
        (r"/healthcheck", HealthHandler),
        (
            r"/static/(.*)",
            NoCacheStaticFileHandler,
            dict(path=os.path.join(path, "static")),
        ),
        (
            r"/(favicon.ico)",
            NoCacheStaticFileHandler,
            dict(path=os.path.join(path, "static")),
        ),
        # Generally, everything behind "/api" in a production instance is not protected by SSO.
        # It should be behind mtls
        (r"/api/v1/get_credentials", GetCredentialsHandler),
        (r"/api/v1/get_roles", GetRolesHandler),
        # Used to autocomplete s3:get to all matching permissions
        (r"/api/v1/policyuniverse/autocomplete/?", AutocompleteHandler),
        (r"/api/v1/get_roles", GetRolesHandler),
        (r"/api/v1/siteconfig/?", SiteConfigHandler),
        (r"/api/v1/profile/?", UserProfileHandler),
        (r"/api/v1/myheaders/?", ApiHeaderHandler),
        (r"/api/v1/policies/typeahead", ApiResourceTypeAheadHandler),
        (r"/api/v2/generate_policy", GeneratePolicyHandler),
        (r"/api/v2/requests", RequestsHandler),
        (r"/api/v2/requests/([a-zA-Z0-9_-]+)", RequestDetailHandler),
        (r"/api/v2/roles/?", RolesHandler),
        (r"/api/v2/roles/(\d{12})", AccountRolesHandler),
        (r"/api/v2/roles/(\d{12})/(.*)", RoleDetailHandler),
        (r"/api/v2/mtls/roles/(\d{12})/(.*)", RoleDetailAppHandler),
        (r"/api/v2/roles/clone/(\d{12})/(.*)", RoleCloneHandler),
        (r"/api/v2/generate_changes/?", GenerateChangesHandler),
        (r"/config/?", DynamicConfigHandler),
        (r"/myheaders/?", HeaderHandler),
        (r"/policies/?", PolicyViewHandler),
        (
            r"/policies/get_policies/?",
            GetPoliciesHandler,
        ),  # Used to search/filter for /policies page
        (r"/policies/edit/(\d{12})/iamrole/(.*)", PolicyEditHandler),
        # Properly routes S3, SQS, SNS policy requests
        (
            r"/policies/edit/(\d{12})/(s3|sqs|sns)(?:/([a-z\-1-9]+))?/(.*)",
            ResourcePolicyEditHandler,
        ),
        (r"/policies/request/([a-zA-Z0-9_-]+)", PolicyReviewHandler),
        (r"/policies/submit_for_review", PolicyReviewSubmitHandler),
        (r"/policies/typeahead", ResourceTypeAheadHandler),
        (r"/swagger", SwaggerHandler),
        (r"/swagger.json", SwaggerJsonGenerator),
        (r"/saml/(.*)", SamlHandler),
        (r"/self_service", SelfServiceHandler),
        (r"/self_service_new", SelfServiceNewHandler),
    ]

    routes.extend(
        internal_routes.get_internal_routes(make_jwt_validator, jwt_validator)
    )

    # Return a JSON 404 for unmatched /api/v2/ requests
    routes.append((r"/api/v2/.*", V2NotFoundHandler))
    routes.append((r".*", Consolme404Handler))

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
        app.sentry_client = AsyncSentryClient(config.get("sentry.dsn"))

    for r in routes:
        try:
            spec.path(urlspec=r)
        except APISpecError:
            # Docstring not specified correctly for endpoint
            log_data = {
                "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                "message": "Unable to add docs for Urlspec.",
                "route": r,
            }
            log.debug(log_data, exc_info=True)
    config.api_spec = spec.to_dict()

    return app

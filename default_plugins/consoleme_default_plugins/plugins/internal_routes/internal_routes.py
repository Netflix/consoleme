import os

import pkg_resources
from consoleme_default_plugins.plugins.internal_routes.handlers.internal_demo_route import (
    InternalDemoRouteHandler,
)

from consoleme.handlers.base import NoCacheStaticFileHandler


class InternalRoutes:
    ui_modules = {}

    def get_internal_routes(self, make_jwt_validator, jwt_validator=None):
        path = pkg_resources.resource_filename("consoleme_internal", "templates")
        internal_routes = [
            (r"/internal_demo_route/?", InternalDemoRouteHandler),
            (
                r"/static_internal/(.*)",
                NoCacheStaticFileHandler,
                dict(path=os.path.join(path, "static")),
            ),
        ]
        return internal_routes


def init():
    """Initialize the internal routes plugin."""
    return InternalRoutes()

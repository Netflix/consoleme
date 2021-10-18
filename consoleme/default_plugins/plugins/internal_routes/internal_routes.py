from consoleme.default_plugins.plugins.internal_routes.handlers.internal_demo_route import (
    InternalDemoRouteHandler,
)


class InternalRoutes:
    ui_modules = {}

    def get_internal_routes(self, make_jwt_validator, jwt_validator=None):
        # The below code can be used with your ConsoleMe Internal package name to generate a path to your internal
        # JavaScript and HTML files, if you wish to render these for the handler.
        # path = pkg_resources.resource_filename("consoleme_internal", "templates")
        internal_routes = [
            (r"/internal_demo_route/?", InternalDemoRouteHandler),
            # An example of serving static internal content is below, which would make use of the template path variable
            # You defined above.
            # (
            #     r"/static_internal/(.*)",
            #     NoCacheStaticFileHandler,
            #     dict(path=os.path.join(path, "static")),
            # ),
        ]
        return internal_routes


def init():
    """Initialize the internal routes plugin."""
    return InternalRoutes()

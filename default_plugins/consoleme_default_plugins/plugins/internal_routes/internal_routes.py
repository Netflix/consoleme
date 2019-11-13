class InternalRoutes:
    ui_modules = {}

    def get_internal_routes(self, make_jwt_validator, jwt_validator=None):
        return []


def init():
    """Initialize the internal routes plugin."""
    return InternalRoutes()

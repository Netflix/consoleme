from consoleme.config import config
from consoleme.handlers.base import BaseHandler
from consoleme.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
log = config.get_logger()


class InternalDemoRouteHandler(BaseHandler):
    """
    This is a route with the simple purpose of showcasing how OSS users can add additional internal-only pages
    to ConsoleMe
    """

    def get_template_path(self):
        # You can define a custom template path here based on the name of your consoleme internal plugin package
        pass

    async def get(self):
        """/internal_demo_route.
        ---
        get:
            description: Shows demo data
            responses:
                200:
                    description: Renders a page with demo data.
        """

        if not self.user:
            return

        stats.count("internal_demo_route.get", tags={"user": self.user})

        log_data = {
            "function": "InternalDemoRouteHandler.get",
            "message": "Incoming request",
            "user": self.user,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }

        log.debug(log_data)

        self.write("Hello world!")

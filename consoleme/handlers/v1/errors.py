"""Error handler."""
from consoleme.config import config
from consoleme.handlers.base import BaseHandler
from consoleme.lib.generic import render_404
from consoleme.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("plugins.metrics"))()

log = config.get_logger()


class Consolme404Handler(BaseHandler):
    """HTTP 404 error handler."""

    async def get(self) -> None:
        """Handle HTTP 404 errors
        ---
        get:
            description:  HTTP 404 errors
            responses:
                200:
                    description: Simple endpoint that returns HTTP 404 and and an image to indicate 404 error.
        """

        if not self.user:
            return

        stats.count("notfound.get", tags={"user": self.user})

        log_data = {
            "function": "Consolme404Handler.get",
            "message": "HTTP 404 not found error",
            "user": self.user,
            "user-agent": self.request.headers.get("User-Agent"),
        }

        log.debug(log_data)

        render_404(self, config)

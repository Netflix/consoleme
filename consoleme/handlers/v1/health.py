"""Health handler."""
from consoleme.handlers.base import TornadoRequestHandler


class HealthHandler(TornadoRequestHandler):
    """Health handler."""

    async def get(self):
        """Healthcheck endpoint
        ---
        get:
            description: Healtcheck endpoint
            responses:
                200:
                    description: Simple endpoint that returns 200 and a string to signify that the server is up.
        """
        self.write("OK")

import ujson as json

from consoleme.config import config
from consoleme.handlers.base import BaseMtlsHandler
from consoleme.lib.crypto import Crypto
from consoleme.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
log = config.get_logger()
crypto = Crypto()
auth = get_plugin_by_name(config.get("plugins.auth", "default_auth"))()


class GetRolesHandler(BaseMtlsHandler):
    """consoleme CLI role handler. Pass ?all=true to URL query to return all roles."""

    def check_xsrf_cookie(self):
        pass

    def initialize(self):
        self.user: str = None
        self.eligible_roles: list = []

    async def get(self):
        """
        /api/v1/get_roles - Endpoint used to get list of roles. Used by weep and newt.
        ---
        get:
            description: Presents json-encoded list of eligible roles for the user.
            responses:
                200:
                    description: Present user with list of eligible roles.
                403:
                    description: User has failed authn/authz.
        """
        self.user: str = self.requester["email"]

        include_all_roles = self.get_arguments("all")
        console_only = True
        if include_all_roles == ["true"]:
            console_only = False

        log_data = {
            "function": "GetRolesHandler.get",
            "user": self.user,
            "console_only": console_only,
            "message": "Writing all eligible user roles",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        stats.count("GetRolesHandler.get", tags={"user": self.user})

        await self.authorization_flow(user=self.user, console_only=console_only)
        self.write(json.dumps(sorted(self.eligible_roles)))
        self.set_header("Content-Type", "application/json")
        await self.finish()

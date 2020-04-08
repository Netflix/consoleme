from operator import itemgetter

from consoleme.config import config
from consoleme.handlers.base import BaseHandler
from consoleme.lib.handler_utils import format_role_name
from consoleme.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()
group_mapping = get_plugin_by_name(config.get("plugins.group_mapping"))()


class AutoLoginHandler(BaseHandler):
    """Display AutoLoginHandler page."""

    def initialize(self):
        """Initialize the Tornado RequestHandler."""
        self.user = None
        self.eligible_roles = None
        self.eligible_accounts = None
        self.groups = None

    async def head(self):
        """Return a 200 for HEAD requests.
        This is mainly for health checks.
        """
        pass

    async def get(self, role=None):
        """Filter role / autologin endpoint
        ---
        get:
            description: Filter eligible roles by role input and render Index page with list of matching roles.
            responses:
                200:
                    description: Index page with filtered eligible user roles
        """
        if not role:
            self.write("You must pass an argument to this endpoint.")
            return

        role = role.lower()

        region = self.request.arguments.get("r", ["us-east-1"])[0]
        redirect = self.request.arguments.get("redirect", [""])[0]

        if not self.user:
            return

        selected_roles = await group_mapping.filter_eligible_roles(role, self)

        log_data = {
            "user": self.user,
            "function": "AutoLoginHandler.get",
            "selected_roles": selected_roles,
            "requested_role": role,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        if not selected_roles:
            log_data["message"] = (
                "You do not have any roles matching your search criteria. "
                "Visit the Request Access tab to request access to a role."
            )
            log.error(log_data)
            # Not authorized
            stats.count(
                "AutoLoginHandler.get",
                tags={"user": self.user, "role": role, "authorized": False},
            )

            await self.render(
                "index.html",
                page_title="ConsoleMe - Console Access",
                user=self.user,
                eligible_roles=self.eligible_roles,
                eligible_accounts=self.eligible_accounts,
                itemgetter=itemgetter,
                recent_roles=True,
                error=log_data["message"],
                region=region,
                redirect=redirect,
                current_page="index",
                format_role_name=format_role_name,
                user_groups=self.groups,
                config=config,
            )
            return

        log_data[
            "message"
        ] = "Showing user authorized roles, or logging them in automatically if only one."
        log.debug(log_data)
        stats.count(
            "AutoLoginHandler.get",
            tags={
                "user": self.user,
                "selected_roles": selected_roles,
                "authorized": True,
            },
        )

        # User is authorized for one or more selected roles

        await self.render(
            "index.html",
            page_title="ConsoleMe - Console Access",
            user=self.user,
            eligible_roles=selected_roles,
            eligible_accounts={},
            itemgetter=itemgetter,
            recent_roles=False,
            error=None,
            region=region,
            redirect=redirect,
            current_page="index",
            format_role_name=format_role_name,
            user_groups=self.groups,
            config=config,
        )

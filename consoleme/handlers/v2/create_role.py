import sys

from consoleme.config import config
from consoleme.handlers.base import BaseHandler
from consoleme.lib.aws import can_create_roles
from consoleme.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()


class CreateRoleViewHandler(BaseHandler):
    async def get(self):
        """
         Get the create role endpoint. Presents react component for creating a blank role / cloning a role
        ---
        description: Authorized users can use this webpage to create a blank role or clone an existing role.
        responses:
            200:
                description: Webpage that allows users to create a blank role or clone an existing role.
            403:
                description: User is unauthorized to view this page
        :return:
        """

        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "GET clone request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "ip": self.ip,
        }
        log.debug(log_data)

        can_create_role = await can_create_roles(self.groups, self.user)
        if not can_create_role:
            stats.count(
                f"{log_data['function']}.unauthorized",
                tags={"user": self.user, "authorized": can_create_role},
            )
            log_data["message"] = "User is unauthorized to view create a role page"
            log.error(log_data)
            self.set_status(403, reason="Unauthorized to view this page")
            self.write_error(403)
            return

        await self.render(
            "create_role.html",
            page_title="ConsoleMe - Create Role",
            user=self.user,
            user_groups=self.groups,
            current_page="create_role",
            config=config,
        )

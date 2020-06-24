import sys

from consoleme.config import config
from consoleme.handlers.base import BaseHandler
from consoleme.lib.aws import can_clone_roles
from consoleme.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()


class CloneViewHandler(BaseHandler):
    async def get(self):
        """
         Get the clone endpoint. Presents react component for cloning a role
        ---
        description: Authorized users can use this webpage to clone a role and specify what attributes to clone.
        responses:
            200:
                description: Webpage that allows user to select what role to clone, as well as what attributes to clone
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

        can_clone_role = await can_clone_roles(self.groups, self.user)
        if not can_clone_role:
            stats.count(
                f"{log_data['function']}.unauthorized",
                tags={"user": self.user, "authorized": can_clone_role},
            )
            log_data["message"] = "User is unauthorized to view clone a role page"
            log.error(log_data)
            self.set_status(403, reason="Unauthorized to view this page")
            self.write_error(403)
            return

        await self.render(
            "clone.html",
            page_title="ConsoleMe - Clone Role",
            user=self.user,
            user_groups=self.groups,
            current_page="clone",
            config=config,
        )

import sys

from consoleme.config import config
from consoleme.handlers.base import BaseHandler
from consoleme.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()


class PolicyReviewV2Handler(BaseHandler):
    """
        Handler for /policies/request_v2/{request_id}

        GET - Get requests v2 page # TODO: add better description

    """

    allowed_methods = ["GET"]

    async def get(self, request_id):

        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "ip": self.ip,
            "policy_request_id": request_id,
        }
        log.debug(log_data)
        stats.count(
            f"{log_data['function']}", tags={"user": self.user},
        )

        await self.render(
            "policy_review_v2.html",
            page_title="ConsoleMe - Policy Review",
            current_page="policies",
            user=self.user,
            user_groups=self.groups,
            config=config,
        )

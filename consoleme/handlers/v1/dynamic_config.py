import json
import sys

import tornado.escape
import tornado.web

from consoleme.config import config
from consoleme.handlers.base import BaseHandler
from consoleme.lib.dynamo import UserDynamoHandler
from consoleme.lib.generic import is_in_group
from consoleme.lib.json_encoder import SetEncoder
from consoleme.lib.plugins import get_plugin_by_name

ddb = UserDynamoHandler()
log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics"))()
aws = get_plugin_by_name(config.get("plugins.aws"))()


class DynamicConfigHandler(BaseHandler):
    async def get(self) -> None:
        """
            Get the dynamic configuration endpoint.
            ---
            description: Presents a YAML-configured editor to allow viewing and modification of dynamic config
            responses:
                200:
                    description: View of dynamic configuration
                403:
                    description: Unauthorized to access this page
        """

        if not self.user:
            return

        if not is_in_group(self.user, self.groups, config.get("application_admin")):
            raise tornado.web.HTTPError(
                403, "Only the owner is authorized to view this page."
            )

        dynamic_config = await ddb.get_dynamic_config_yaml()

        await self.render(
            "dynamic_config.html",
            page_title="ConsoleMe - Dynamic Config Editor",
            current_page="config",
            user=self.user,
            user_groups=self.groups,
            config=config,
            dyanmic_config=dynamic_config,
        )

    async def post(self):
        """
            Post an update to the dynamic configuration endpoint.
            ---
            description: Update dynamic configuration
            responses:
                200:
                    description: Update successful.
                403:
                    description: Unauthorized to access this page
        """

        if not self.user:
            return
        if not is_in_group(self.user, self.groups, config.get("application_admin")):
            raise tornado.web.HTTPError(
                403, "Only the owner is authorized to view this page."
            )
        result = {"status": "success"}
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": self.user,
        }
        log.debug(log_data)

        data = tornado.escape.json_decode(self.request.body)
        try:
            await ddb.update_dynamic_config(data["new_config"], self.user)
        except Exception as e:
            result["status"] = "error"
            result["error"] = e
            self.write(json.dumps(result, cls=SetEncoder))
            await self.finish()
            return

        result["new_config"] = data["new_config"]
        self.write(result)
        await self.finish()
        return

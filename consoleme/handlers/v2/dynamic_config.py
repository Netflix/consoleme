import json
import sys
from hashlib import sha256

import sentry_sdk
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


class DynamicConfigApiHandler(BaseHandler):
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

        self.write(
            {
                "dynamicConfig": dynamic_config.decode("utf-8"),
                "sha256": sha256(dynamic_config).hexdigest(),
            }
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
        existing_dynamic_config = await ddb.get_dynamic_config_yaml()
        if existing_dynamic_config:
            existing_dynamic_config_sha256 = sha256(existing_dynamic_config).hexdigest()
        else:
            existing_dynamic_config_sha256 = None
        result = {"status": "success"}
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": self.user,
            "existing_dynamic_config_sha256": existing_dynamic_config_sha256,
        }
        log.debug(log_data)

        data = tornado.escape.json_decode(self.request.body)
        try:
            existing_sha256 = data.get("existing_sha256")
            new_sha256 = sha256(data["new_config"].encode("utf-8")).hexdigest()
            if existing_sha256 == new_sha256:
                raise Exception(
                    "You didn't change the dynamic configuration. Try again!"
                )
            if (
                existing_dynamic_config_sha256
                and not existing_dynamic_config_sha256 == existing_sha256
            ):
                raise Exception(
                    "Dynamic configuration was updated by another user before your changes were processed. "
                    "Please refresh your page and try again."
                )

            await ddb.update_dynamic_config(data["new_config"], self.user)
        except Exception as e:
            result["status"] = "error"
            result["error"] = f"There was an error processing your request: {e}"
            sentry_sdk.capture_exception()
            self.write(json.dumps(result, cls=SetEncoder))
            await self.finish()
            return

        result["newConfig"] = data["new_config"]
        result["newsha56"] = new_sha256
        self.write(result)
        await self.finish()
        return

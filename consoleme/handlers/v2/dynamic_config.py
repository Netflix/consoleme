import json
import sys
from hashlib import sha256

import sentry_sdk
import tornado.escape
import tornado.web

from consoleme.celery_tasks.celery_tasks import app as celery_app
from consoleme.config import config
from consoleme.handlers.base import BaseHandler
from consoleme.lib.auth import can_edit_dynamic_config
from consoleme.lib.dynamo import UserDynamoHandler
from consoleme.lib.json_encoder import SetEncoder
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.redis import RedisHandler

ddb = UserDynamoHandler()
log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
aws = get_plugin_by_name(config.get("plugins.aws", "default_aws"))()
red = RedisHandler().redis_sync()


class DynamicConfigApiHandler(BaseHandler):
    def on_finish(self) -> None:
        if self.request.method != "POST":
            return
        # Force a refresh of credential authorization mapping in current region
        # TODO: Trigger this to run cross-region
        # TODO: Delete server-side user-role cache intelligently so users get immediate access
        celery_app.send_task(
            "consoleme.celery_tasks.celery_tasks.cache_credential_authorization_mapping",
            countdown=config.get("dynamic_config.dynamo_load_interval"),
        )

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

        if not can_edit_dynamic_config(self.user, self.groups):
            raise tornado.web.HTTPError(
                403, "Only application admins are authorized to view this page."
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
        if not can_edit_dynamic_config(self.user, self.groups):
            raise tornado.web.HTTPError(
                403, "Only application admins are authorized to view this page."
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
        # Force a refresh of dynamic configuration in the current region. Other regions will need to wait until the
        # next background thread refreshes it automatically. By default, this happens every 60 seconds.
        config.CONFIG.load_config_from_dynamo(ddb=ddb, red=red)
        return

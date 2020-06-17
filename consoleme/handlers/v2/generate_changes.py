import sys

from pydantic import ValidationError
from tornado.escape import json_decode

from consoleme.config import config
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.lib.change_request import generate_change_model_array
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.models import ChangeGeneratorModelArray

log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics"))()


class GenerateChangesHandler(BaseAPIV2Handler):
    """Handler for /api/v2/generate_changes

    Generates ChangeModelArray from ChangeGeneratorModelArray.
    """

    allowed_methods = ["POST"]

    async def post(self):
        """
        POST /api/v2/generate_changes
        """
        if not self.user:
            self.write_error(403, message="No user detected")
            return

        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user-agent": self.request.headers.get("User-Agent"),
            "ip": self.ip,
            "request_id": self.request_uuid,
        }
        body_dict = json_decode(self.request.body)

        # Override user attribute for each change
        for change in body_dict["changes"]:
            change["user"] = self.user
        try:
            # Validate the model
            changes = ChangeGeneratorModelArray.parse_obj(body_dict)

            # Loop through the raw json object to retrieve attributes that would be parsed out in the
            # ChangeGeneratorModelArray, such as bucket_prefix for S3ChangeGeneratorModel
            change_model_array = await generate_change_model_array(changes)
        except ValidationError as e:
            log_data["message"] = "Validation Exception"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.validation_exception", tags={"user": self.user}
            )
            self.write_error(400, message="Error validating input: " + str(e))
            return
        except NotImplementedError:
            log_data["message"] = "Unknown Generator Type Exception"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.unknown_generator_type",
                tags={"user": self.user},
            )
            self.write_error(
                501, message="Error: This generator_type has not been implemented"
            )
            return
        except Exception as e:
            log_data["message"] = "Unknown Exception ocurred while generating changes"
            log.error(log_data, exc_info=True)
            stats.count(f"{log_data['function']}.exception", tags={"user": self.user})
            config.sentry.captureException(tags={"user": self.user})
            self.write_error(500, message="Error generating changes: " + str(e))
            raise  # TODO: Revert this before committing. For Dev.

        log_data["message"] = "Successfully generated changes requested"
        log.info(log_data)
        stats.count(f"{log_data['function']}.success", tags={"user": self.user})
        self.write(change_model_array.json())

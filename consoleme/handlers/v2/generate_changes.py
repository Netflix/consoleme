import sys

import sentry_sdk
from pydantic import ValidationError

from consoleme.config import config
from consoleme.exceptions.exceptions import InvalidRequestParameter
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.lib.change_request import generate_change_model_array
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.models import ChangeGeneratorModelArray

log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()


class GenerateChangesHandler(BaseAPIV2Handler):
    """Handler for /api/v2/generate_changes

    Generates a ChangeModelArray from ChangeGeneratorModelArray
    """

    allowed_methods = ["POST"]

    async def post(self):
        """
        POST /api/v2/generate_changes

        Generates a ChangeModelArray JSON from ChangeGeneratorModelArray JSON.

        Request example:

        {"changes": [
            {
                "principal": {
                    "principal_arn": "arn:aws:iam::123456789012:role/aRole",
                    "principal_type": "AwsResource"
                },
                "generator_type": "s3",
                "resource_arn": ["arn:aws:s3:::123456789012-bucket"],
                "bucket_prefix": "/*",
                "effect": "Allow",
                "action_groups": [
                    "get",
                    "list"
                ]
            }
        ]}

        Response example:

        { "changes" : [
                {
                    "principal": {
                        "principal_arn": "arn:aws:iam::123456789012:role/aRole",
                        "principal_type": "AwsResource"
                    },
                    "change_type": "inline_policy",
                    "resource_arn": [
                        "arn:aws:s3:::123456789012-bucket"
                    ],
                    "resource": null,
                    "condition": null,
                    "policy_name": "cm_user_1592499820_gmli",
                    "new": true,
                    "policy": {
                        "version": "2012-10-17",
                        "statements": null,
                        "policy_document": "{\"Version\":\"2012-10-17\",\"Statement\":[[{\"Action\"...",
                        "policy_sha256": "cb300def8dd1deaf4db2bfeef4bc6fc740be18e8ccae74c399affe781f82ba6e"
                    },
                    "old_policy": null
                }
            ]
        }
        """

        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user-agent": self.request.headers.get("User-Agent"),
            "ip": self.ip,
            "request_id": self.request_uuid,
        }

        try:
            # Validate the model
            changes = ChangeGeneratorModelArray.parse_raw(self.request.body)

            # Override user attribute for each change
            for change in changes.changes:
                change.user = self.user

            # Loop through the raw json object to retrieve attributes that would be parsed out in the
            # ChangeGeneratorModelArray, such as bucket_prefix for S3ChangeGeneratorModel
            change_model_array = await generate_change_model_array(changes)
        except (InvalidRequestParameter, ValidationError) as e:
            log_data["message"] = "Validation Exception"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.validation_exception", tags={"user": self.user}
            )
            self.write_error(400, message="Error validating input: " + str(e))
            return
        except Exception as e:
            log_data["message"] = "Unknown Exception occurred while generating changes"
            log.error(log_data, exc_info=True)
            stats.count(f"{log_data['function']}.exception", tags={"user": self.user})
            sentry_sdk.capture_exception(tags={"user": self.user})
            self.write_error(500, message="Error generating changes: " + str(e))
            return

        log_data["message"] = "Successfully generated changes requested"
        log.info(log_data)
        stats.count(f"{log_data['function']}.success", tags={"user": self.user})
        self.write(change_model_array.json())

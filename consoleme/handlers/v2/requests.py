import sys

from pydantic import ValidationError

from consoleme.config import config
from consoleme.exceptions.exceptions import InvalidRequestParameter, MustBeFte
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.v2.requests import generate_request_from_change_model_array
from consoleme.models import RequestCreationModel

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()


class RequestsHandler(BaseAPIV2Handler):
    """Handler for /api/v2/requests

    Allows read access to a list of requests. Returned requests are
    limited to what the requesting user has access to.
    """

    allowed_methods = ["GET", "POST"]

    async def get(self):
        """
        GET /api/v2/requests
        """
        tags = {
            "user": self.user,
        }
        stats.count("RequestsHandler.get", tags=tags)
        log_data = {
            "function": "RequestsHandler.get",
            "user": self.user,
            "message": "Writing all available requests",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Get requests")

    async def post(self):
        """
        POST /api/v2/requests
        """

        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")

        tags = {
            "user": self.user,
        }
        stats.count("RequestsHandler.post", tags=tags)
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": self.user,
            "message": "Create request initialization",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "ip": self.ip,
        }
        log.debug(log_data)
        try:
            # Validate the model
            changes = RequestCreationModel.parse_raw(self.request.body)
            extended_request = await generate_request_from_change_model_array(
                changes, self.user
            )
            log_data["request"] = extended_request.json()
            log.debug(log_data)
        except (InvalidRequestParameter, ValidationError) as e:
            log_data["message"] = "Validation Exception"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.validation_exception", tags={"user": self.user}
            )
            self.write_error(400, message="Error validating input: " + str(e))
            return
        except Exception as e:
            log_data["message"] = "Unknown Exception occurred while parsing request"
            log.error(log_data, exc_info=True)
            stats.count(f"{log_data['function']}.exception", tags={"user": self.user})
            config.sentry.captureException(tags={"user": self.user})
            self.write_error(500, message="Error parsing request: " + str(e))
            return

        # TODO: put generated request in Dynamo
        # TODO: auto-approval probes
        # TODO: admin self-approval stuff
        # self.write(extended_request.json())
        self.write_error(501, message="Create request")


class RequestDetailHandler(BaseAPIV2Handler):
    """Handler for /api/v2/requests/{request_id}

    Allows read and update access to a specific request.
    """

    allowed_methods = ["GET", "PUT"]

    async def get(self, request_id):
        """
        GET /api/v2/requests/{request_id}
        """
        tags = {
            "user": self.user,
        }
        stats.count("RequestDetailHandler.get", tags=tags)
        log_data = {
            "function": "RequestDetailHandler.get",
            "user": self.user,
            "message": "Writing request details",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Get request details")

    async def put(self, request_id):
        """
        PUT /api/v2/requests/{request_id}
        """
        tags = {
            "user": self.user,
        }
        stats.count("RequestDetailHandler.put", tags=tags)
        log_data = {
            "function": "RequestDetailHandler.put",
            "user": self.user,
            "message": "Updating request details",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Update request details")

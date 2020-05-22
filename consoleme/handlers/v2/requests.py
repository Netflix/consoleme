import ujson as json

from consoleme.config import config
from consoleme.handlers.base import BaseJSONHandler, BaseAPIV2Handler
from consoleme.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()


class RequestsHandler(BaseAPIV2Handler):
    """Handler for /api/v2/requests

    Allows read access to a list of requests. Returned requests are
    limited to what the requesting user has access to.
    """

    allowed_methods = ["GET", "POST"]

    def __init__(self, *args, **kwargs):
        # TODO(psanders): Use actual JWT validator
        super().__init__(jwt_validator=lambda x: {}, *args, **kwargs)

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
        tags = {
            "user": self.user,
        }
        stats.count("RequestsHandler.post", tags=tags)
        log_data = {
            "function": "RequestsHandler.post",
            "user": self.user,
            "message": "Creating request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Create request")


class RequestDetailHandler(BaseAPIV2Handler):
    """Handler for /api/v2/requests/{request_id}

    Allows read and update access to a specific request.
    """

    allowed_methods = ["GET", "PUT"]

    def __init__(self, *args, **kwargs):
        # TODO(psanders): Use actual JWT validator
        super().__init__(jwt_validator=lambda x: {}, *args, **kwargs)

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

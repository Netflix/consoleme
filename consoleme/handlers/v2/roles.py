import ujson as json

from consoleme.config import config
from consoleme.handlers.base import BaseJSONHandler
from consoleme.lib.crypto import Crypto
from consoleme.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()
crypto = Crypto()
auth = get_plugin_by_name(config.get("plugins.auth"))()


class RolesHandler(BaseJSONHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(jwt_validator=lambda x: {}, *args, **kwargs)

    def options(self, *args):
        self.set_header("Access-Control-Allow-Headers", "GET")
        self.set_header("Content-Length", "0")
        self.set_status(204)
        self.finish()

    async def get(self):
        """
        GET /api/v2/roles
        """
        log_data = {
            "function": "RolesHandler.get",
            "user": self.user,
            "message": "Writing all eligible user roles",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Get roles")


class AccountRolesHandler(BaseJSONHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(jwt_validator=lambda x: {}, *args, **kwargs)

    def options(self, *args):
        self.set_header("Access-Control-Allow-Headers", "GET")
        self.set_header("Content-Length", "0")
        self.set_status(204)
        self.finish()

    async def get(self):
        """
        GET /api/v2/roles/{accountNumber}
        """
        log_data = {
            "function": "AccountRolesHandler.get",
            "user": self.user,
            "message": "Writing all eligible user roles",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Get roles by account")


class RoleDetailHandler(BaseJSONHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(jwt_validator=lambda x: {}, *args, **kwargs)

    def options(self, *args):
        self.set_header("Access-Control-Allow-Headers", "GET,PUT")
        self.set_header("Content-Length", "0")
        self.set_status(204)
        self.finish()

    async def get(self):
        """
        GET /api/v2/roles/{accountNumber}/{roleName}
        """
        log_data = {
            "function": "RoleDetailHandler.get",
            "user": self.user,
            "message": "Writing all eligible user roles",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Get role details")

    async def put(self):
        """
        PUT /api/v2/roles/{accountNumber}/{roleName}
        """
        log_data = {
            "function": "RoleDetailHandler.put",
            "user": self.user,
            "message": "Writing all eligible user roles",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Update role details")

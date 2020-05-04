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
    """Handler for /api/v2/roles

    Allows read access to a list of roles across all accounts. Returned roles are
    limited to what the requesting user has access to.
    """

    allowed_methods = ["GET"]

    def __init__(self, *args, **kwargs):
        # TODO(psanders): Use actual JWT validator
        super().__init__(jwt_validator=lambda x: {}, *args, **kwargs)

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
    """Handler for /api/v2/roles/{account_number}

    Allows read access to a list of roles by account. Roles are limited to what the
    requesting user has access to.
    """

    allowed_methods = ["GET"]

    def __init__(self, *args, **kwargs):
        # TODO(psanders): Use actual JWT validator
        super().__init__(jwt_validator=lambda x: {}, *args, **kwargs)

    async def get(self, account_id):
        """
        GET /api/v2/roles/{account_id}
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
    """Handler for /api/v2/roles/{accountNumber}/{roleName}

    Allows read and update access to a specific role in an account.
    """

    allowed_methods = ["GET", "PUT"]

    def __init__(self, *args, **kwargs):
        # TODO(psanders): Use actual JWT validator
        super().__init__(jwt_validator=lambda x: {}, *args, **kwargs)

    async def get(self, account_number, role_name):
        """
        GET /api/v2/roles/{account_number}/{role_name}
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

    async def put(self, account_id, role_name):
        """
        PUT /api/v2/roles/{account_number}/{role_name}
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

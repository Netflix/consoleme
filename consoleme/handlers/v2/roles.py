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
    """
    Handler for /api/v2/roles
    ---
    get:
        description: Returns a list of roles the current user can access.
        responses:
            200:
                description: List of roles the current user can access
            403:
                description: Unauthorized
    options:
        description: Endpoint options
        responses:
            200:
                description: Options response
    """

    def __init__(self, *args, **kwargs):
        # TODO(psanders): Use actual JWT validator
        super().__init__(jwt_validator=lambda x: {}, *args, **kwargs)

    def options(self, *args):
        """
        OPTIONS /api/v2/roles
        ---
        options:
            description: foo
        """
        self.set_header("Access-Control-Allow-Headers", "GET")
        self.set_header("Content-Length", "0")
        self.set_status(204)
        self.finish()

    async def get(self):
        """
        GET /api/v2/roles
        ---
        get:
            description: foo
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
    """
    Handler for /api/v2/roles/{account_number}
    The following annotation only works if it's commented out. That bothers me so much. Help.
    TODO(psanders): whyyyyyy
    ---
    # options:
    #     description: Endpoint options
    #     parameters:
    #         - in: path
    #           name: accountNumber
    #           required: true
    #           example: 012345678901
    #           schema:
    #               type: string
    #               pattern: '^\d{12}$'
    #     responses:
    #         200:
    #             description: Options response
    # get:
    #     description: Returns a list of roles the current user can access in a given account.
    #     parameters:
    #         - in: path
    #           name: accountNumber
    #           required: true
    #           example: 012345678901
    #           schema:
    #               type: string
    #               pattern: '^\d{12}$'
    #     responses:
    #     200:
    #         description: List of roles the current user can access in a given account
    #     403:
    #         description: Unauthorized
    """

    def __init__(self, *args, **kwargs):
        # TODO(psanders): Use actual JWT validator
        super().__init__(jwt_validator=lambda x: {}, *args, **kwargs)

    def options(self, *args):
        """
        OPTIONS /api/v2/roles/{account_number}
        ---
        options:
            description: foo
        """
        self.set_header("Access-Control-Allow-Headers", "GET")
        self.set_header("Content-Length", "0")
        self.set_status(204)
        self.finish()

    async def get(self, account_id):
        """
        GET /api/v2/roles/{account_id}
        ---
        get:
            description: foo
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
    """
    OPTIONS /api/v2/roles/{account_number}/{role_name}
    ---
    options:
        description: Endpoint options
        parameters:
            - in: path
              name: accountNumber
              required: true
              example: 012345678901
              schema:
                  type: string
                  pattern: '^\d{12}$'
            - in: path
              name: roleName
              required: true
              example: fake_account_admin
              schema:
                  type: string
        responses:
            200:
                description: Options response
    get:
        description: Returns details about a given role in an account.
        parameters:
            - in: path
              name: accountNumber
              required: true
              example: 012345678901
              schema:
                  type: string
                  pattern: '^\d{12}$'
            - in: path
              name: roleName
              required: true
              example: fake_account_admin
              schema:
                  type: string
        responses:
            200:
                description: Details about a given role in an account.
            403:
                description: Unauthorized
    put:
        description: Update a given role in an account.
        parameters:
            - in: path
              name: accountNumber
              required: true
              example: 012345678901
              schema:
                  type: string
                  pattern: '^\d{12}$'
            - in: path
              name: roleName
              required: true
              example: fake_account_admin
              schema:
                  type: string
        responses:
            200:
                description: Role updated successfully
            403:
                description: Unauthorized
    """

    def __init__(self, *args, **kwargs):
        # TODO(psanders): Use actual JWT validator
        super().__init__(jwt_validator=lambda x: {}, *args, **kwargs)

    def options(self, *args):
        """
        OPTIONS /api/v2/roles/{account_number}/{role_name}
        ---
        options:
            description: foo
        """
        self.set_header("Access-Control-Allow-Headers", "GET,PUT")
        self.set_header("Content-Length", "0")
        self.set_status(204)
        self.finish()

    async def get(self, account_number, role_name):
        """
        GET /api/v2/roles/{account_number}/{role_name}
        ---
        get:
            description: foo
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
        ---
        put:
            description: foo
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

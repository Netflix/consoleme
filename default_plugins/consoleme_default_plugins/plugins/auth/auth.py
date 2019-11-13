import sys
import time

from consoleme.config import config
from consoleme.exceptions.exceptions import InvalidCertificateException, NoUserException
from consoleme.lib.plugins import get_plugin_by_name


log = config.get_logger("consoleme")
stats = get_plugin_by_name(config.get("plugins.metrics"))()


class Auth:
    """The Auth class authenticates the user and provides the user's groups."""

    def __init__(self, headers: dict = None):
        """Initialize the auth class."""
        self.headers = headers

    async def get_user(self, headers: dict = None):
        """Get the user identity."""
        if config.get("auth.get_user_by_header"):
            return await self.get_user_by_header(headers)
        else:
            raise Exception("auth.get_user not configured")

    async def get_user_by_header(self, headers: dict):
        """Get the user identity via plaintext header."""
        if not headers:
            raise Exception(
                "auth.get_user_by_header enabled, but no headers were passed in"
            )

        user_header_name = config.get("auth.user_header_name")
        if not user_header_name:
            raise Exception(
                "auth.user_header_name configuration not set, but auth.get_user_by_header is enabled."
            )

        user = headers.get(user_header_name)
        if not user:
            raise NoUserException("User header '{}' is empty.".format(user_header_name))
        return user

    async def get_groups(
        self, user: str, headers=None, get_header_groups=False, only_direct=True
    ):
        """Get the user's groups."""
        groups = []
        if get_header_groups or config.get("auth.get_groups_by_header"):
            header_groups = await self.get_groups_by_header(headers)
            if header_groups:
                groups.extend(header_groups)
        if not groups:
            log.error(
                {
                    "message": "auth.get_groups not configured properly or no groups were obtained."
                },
                exc_info=True,
            )
        return list(set(groups))

    async def get_groups_by_header(self, headers: dict):
        """Get the user's groups by plaintext header."""
        groups = []

        if not headers:
            log_data = {
                "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                "message": "No headers present.",
            }
            log.debug(log_data, exc_info=True)
            return groups

        groups_header_name = config.get("auth.groups_header_name", None)
        if not groups_header_name:
            log_data = {
                "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                "message": "Group header name not configured.",
            }
            log.debug(log_data, exc_info=True)
            raise Exception(
                "auth.groups_header_name configuration not set, but auth.get_groups_by_header is enabled."
            )

        if headers.get(groups_header_name):
            groups = headers[groups_header_name].split(",")

        return groups

    async def extract_certificate(self, headers: dict):
        raise NotImplementedError()

    async def extract_user_from_certificate(self, headers: dict):
        return await self.extract_certificate(headers)

    async def get_cert_age_seconds(self, headers: dict):
        """Retrieve age of mtls certificate."""
        current_time = int(time.time())
        cert = await self.extract_certificate(headers)
        return current_time - int(cert.get("notBefore"))

    async def validate_certificate(self, headers: dict):
        for header in config.get("cli_auth.required_headers", [{}]):
            for k, v in header.items():
                if headers.get(k) != v:
                    stats.count("auth.validate_certificate.error")
                    error = "Header {} is supposed to equal {}, but it equals {}.".format(
                        k, v, headers.get(k)
                    )
                    log_data = {
                        "function": "auth.validate_certificate",
                        "message": error,
                    }
                    log.error(log_data)
                    raise InvalidCertificateException(error)
        return True

    async def is_user_contractor(self, user):
        return False

    async def validate_and_return_api_caller(self, headers: dict):
        for header in config.get("cli_auth.required_headers", [{}]):
            for k, v in header.items():
                if headers.get(k) != v:
                    raise Exception(
                        f"Header {k} is supposed to equal {v}, but it equals {headers.get(k)}."
                    )
        cert = await self.extract_user_from_certificate(headers)
        user = cert.get("name")
        if not user or user not in config.get("api_auth.valid_entities", []):
            raise Exception("Not authorized to call this API with that certificate.")
        return user

    async def get_user_info(self, user: str, object: bool = False):
        raise NotImplementedError()

    async def get_group_info(self, group, members=True):
        raise NotImplementedError()

    async def put_group_attribute(self, group, attribute_name, attribute_value):
        raise NotImplementedError()

    async def put_group_attributes(self, group, attributes):
        raise NotImplementedError()

    async def is_user_in_group(self, user, group, only_direct=True):
        raise NotImplementedError()

    async def is_requestable(self, group):
        raise NotImplementedError()

    async def does_user_exist(self, user):
        raise NotImplementedError()

    async def get_group_attribute(self, group, attribute_name):
        raise NotImplementedError()

    async def get_secondary_approvers(self, group):
        """Return a list of secondary approvers for a group."""
        raise NotImplementedError()

    async def get_groups_with_attribute_name_value(
        self, attribute_name, attribute_value
    ):
        raise NotImplementedError()

    async def get_users_with_attribute_name_value(
        self, attribute_name, attribute_value
    ):
        raise NotImplementedError()

    async def is_group_requestable(self, group):
        raise NotImplementedError()

    async def get_all_requestable_groups(self):
        raise NotImplementedError()

    async def get_group_memberships(self, user, scopes=[], only_direct=True) -> list:
        return []

    async def get_group_members(self, group):
        raise NotImplementedError()

    async def get_user_attribute(self, user, attribute_name):
        raise NotImplementedError()

    async def get_or_create_user_role_name(self, user):
        user_role_name_attribute = await self.get_user_attribute(user, "user_role_name")
        if not user_role_name_attribute:
            return await self.generate_and_store_user_role_name(user)
        user_role_name = user_role_name_attribute.value
        return user_role_name

    async def generate_and_store_user_role_name(self, user):
        (username, domain) = user.split("@")
        return f"{username}-{domain}"


def init():
    """Initialize the auth plugin."""
    return Auth()

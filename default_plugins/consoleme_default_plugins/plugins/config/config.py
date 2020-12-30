import hashlib
import os
import urllib.parse
from typing import List


class Config:
    @staticmethod
    def get_config_location():
        if os.environ.get("CONFIG_LOCATION"):
            return os.environ.get("CONFIG_LOCATION")
        config_locations: List[str] = [
            f"{os.curdir}/consoleme.yaml",
            os.path.expanduser("~/.config/consoleme/config.yaml"),
            "/etc/consoleme/config/config.yaml",
            "example_config/example_config_development.yaml",
        ]
        for loc in config_locations:
            if os.path.exists(loc):
                return loc
        raise Exception(
            "Unable to find ConsoleMe's configuration. It either doesn't exist, or "
            "ConsoleMe doesn't have permission to access it. Please set the CONFIG_LOCATION environment variable "
            "to the path of the configuration. Otherwise, ConsoleMe will automatically search for the configuration "
            f"in these locations: {', '.join(config_locations)}"
        )

    @staticmethod
    def internal_functions(cfg=None):
        cfg = cfg or {}
        pass

    @staticmethod
    def is_contractor(user):
        return False

    @staticmethod
    def get_employee_photo_url(user):
        from consoleme.config import config

        # Try to get a custom employee photo url by formatting a string provided through configuration

        custom_employee_photo_url = config.get(
            "get_employee_photo_url.custom_employee_url", ""
        ).format(user=user)
        if custom_employee_photo_url:
            return custom_employee_photo_url

        # Fall back to Gravatar
        gravatar_url = (
            "https://www.gravatar.com/avatar/"
            + hashlib.md5(user.lower().encode("utf-8")).hexdigest()
            + "?"
        )
        gravatar_url += urllib.parse.urlencode({"d": "mp"})
        return gravatar_url

    @staticmethod
    def get_employee_info_url(user):
        return None


def init():
    """Initialize the Config plugin."""
    return Config()

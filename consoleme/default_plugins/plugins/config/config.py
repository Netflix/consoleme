import hashlib
import os
import urllib.parse
from typing import List

from consoleme.lib.aws_secret_manager import get_aws_secret


def split_s3_path(s3_path):
    path_parts = s3_path.replace("s3://", "").split("/")
    b = path_parts.pop(0)
    k = "/".join(path_parts)
    return b, k


class Config:
    @staticmethod
    def get_config_location():
        config_location = os.environ.get("CONFIG_LOCATION")
        default_save_location = f"{os.curdir}/consoleme.yaml"
        if config_location:
            if config_location.startswith("s3://"):
                import boto3

                client = boto3.client("s3")
                bucket, key = split_s3_path(config_location)
                obj = client.get_object(Bucket=bucket, Key=key)
                config_data = obj["Body"].read()
                with open(default_save_location, "w") as f:
                    f.write(config_data.decode())
            elif config_location.startswith("AWS_SECRETS_MANAGER:"):
                secret_name = "".join(config_location.split("AWS_SECRETS_MANAGER:")[1:])
                config_data = get_aws_secret(
                    secret_name, os.environ.get("EC2_REGION", "us-east-1")
                )
                with open(default_save_location, "w") as f:
                    f.write(config_data)
            else:
                return config_location
        config_locations: List[str] = [
            default_save_location,
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
            "to the path of the configuration, or to an s3 location with your configuration"
            "(i.e: s3://YOUR_BUCKET/path/to/config.yaml). Otherwise, ConsoleMe will automatically search for the"
            f"configuration in these locations: {', '.join(config_locations)}"
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
            + hashlib.md5(user.lower().encode("utf-8")).hexdigest()  # nosec
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

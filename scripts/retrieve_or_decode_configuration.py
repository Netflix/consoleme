"""
    This script will retrieve and save ConsoleMe's configuration if the specified environment variables are defined.
    This is useful for Docker / ECS.

    * If `CONSOLEME_CONFIG_B64` is defined, this script will decode the Base64 encoded string and save the configuration
    file in the location specified by `CONFIG_LOCATION` (Defaults to: /etc/consoleme/config/config.yaml)

    * If `CONSOLEME_CONFIG_S3` is defined, this script will download the configuration from S3, and store it in the
    location specified by `CONFIG_LOCATION` (Defaults to: /etc/consoleme/config/config.yaml)

    Usage:
        You can Base64 encode ConsoleMe's configuration with the following command:

        export CONSOLEME_CONFIG_B64=`base64 /path/to/your/consoleme/config.yaml`

        Alternatively, you can upload ConsoleMe's configuration to S3 and this script will attempt to download it:

        export CONSOLEME_CONFIG_S3=`s3://location/to/your/config.yaml`

"""

import base64
import errno
import logging
import os
import sys

import boto3

format_c = "%(asctime)s - %(levelname)s - %(name)s - [%(filename)s:%(lineno)s - %(funcName)s() ] - %(message)s"
logging.basicConfig(level=logging.DEBUG, format=format_c)


def split_s3_path(s3_path):
    path_parts = s3_path.replace("s3://", "").split("/")
    b = path_parts.pop(0)
    k = "/".join(path_parts)
    return b, k


def make_directories(loc):
    head, _ = os.path.split(loc)
    try:
        os.makedirs(head)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


save_location = os.environ.get("CONFIG_LOCATION", "/etc/consoleme/config/config.yaml")

base64_config = os.environ.get("CONSOLEME_CONFIG_B64")
s3_config_path = os.environ.get("CONSOLEME_CONFIG_S3")

if not base64_config and not s3_config_path:
    logging.warning(
        "Neither the CONSOLEME_CONFIG_B64 or CONSOLEME_CONFIG_S3 environment variables are defined. This is required "
        "to retrieve a custom ConsoleMe configuration via S3, or decode it from Base64. This warning is safe to ignore "
        "if you're just testing ConsoleMe and want to rely on the default configuration."
    )
    sys.exit(0)
if base64_config and s3_config_path:
    logging.warning(
        "ConsoleMe only expects one environment variable for configuration retrieval to be defined, but found two. "
        "Please only set one of: CONSOLEME_CONFIG_B64 or CONSOLEME_CONFIG_S3."
    )
    sys.exit(1)
if base64_config:
    decoded_config = base64.b64decode(base64_config)
    logging.info(f"Decoded ConsoleMe's configuration and saving to {save_location}")
    make_directories(save_location)
    with open(save_location, "w") as f:
        f.write(decoded_config.decode())
elif s3_config_path:
    client = boto3.client("s3")
    bucket, key = split_s3_path(s3_config_path)
    obj = client.get_object(Bucket=bucket, Key=key)
    s3_object_content = obj["Body"].read()
    logging.info(
        f"Retrieved ConsoleMe's configuration from {s3_config_path} and writing  to {save_location}"
    )
    make_directories(save_location)
    with open(save_location, "w") as f:
        f.write(s3_object_content.decode())

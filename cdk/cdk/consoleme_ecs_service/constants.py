"""
Defining constants and resolving variables through configuration file
"""

import yaml

config_yaml = yaml.load(open("config.yaml"), Loader=yaml.FullLoader)

domain_prefix = config_yaml["domain_prefix"]

BASE_NAME = "ConsolemeECS"
SPOKE_BASE_NAME = "ConsolemeSpoke"

APPLICATION_PREFIX = "consoleme-" + domain_prefix
APPLICATION_SUFFIX = "secure".lower()
HOSTED_ZONE_ID = config_yaml["hosted_zone_id"]
HOSTED_ZONE_NAME = config_yaml["hosted_zone_name"]
ADMIN_TEMP_PASSWORD = config_yaml["admin_temp_password"]
CONTAINER_IMAGE = config_yaml["container_image"]

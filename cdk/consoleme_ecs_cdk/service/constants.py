"""
Defining constants and resolving variables through configuration file
"""

import yaml

config_yaml = yaml.load(open("config.yaml"), Loader=yaml.FullLoader)

domain_prefix = config_yaml["domain_prefix"]

BASE_NAME = "ConsoleMeECS"
SPOKE_BASE_NAME = "ConsoleMeSpoke"
MAIN_ACCOUNT_ID = config_yaml["main_account"]

APPLICATION_PREFIX = "consoleme-" + domain_prefix
APPLICATION_SUFFIX = "secure".lower()
HOSTED_ZONE_ID = config_yaml["hosted_zone_id"]
HOSTED_ZONE_NAME = config_yaml["hosted_zone_name"]
ADMIN_TEMP_PASSWORD = config_yaml["admin_temp_password"]
USE_PUBLIC_DOCKER_IMAGE = config_yaml["use_public_docker_image"]
DOCKER_IMAGE = "consoleme/consoleme"
MIN_CAPACITY = config_yaml["min_capacity"]
MAX_CAPACITY = config_yaml["max_capacity"]
CONFIG_SECRET_NAME = "ConsoleMeConfigSecret"

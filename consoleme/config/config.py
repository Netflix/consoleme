"""Configuration handling library."""
import collections
import datetime
import logging
import os
import socket
import sys
import time
from logging import LoggerAdapter, LogRecord
from threading import Timer
from typing import Any, Dict, List, Optional, Union

import boto3
import logmatic
import ujson as json
import yaml
from asgiref.sync import async_to_sync
from pytz import timezone

from consoleme.lib.aws_secret_manager import get_aws_secret
from consoleme.lib.plugins import get_plugin_by_name

config_plugin_entrypoint = os.environ.get(
    "CONSOLEME_CONFIG_ENTRYPOINT", "default_config"
)
config_plugin = get_plugin_by_name(config_plugin_entrypoint)


def dict_merge(dct: dict, merge_dct: dict):
    """Recursively merge two dictionaries, including nested dicts"""
    for k, v in merge_dct.items():
        if (
            k in dct
            and isinstance(dct[k], dict)
            and isinstance(merge_dct[k], collections.Mapping)
        ):
            dict_merge(dct[k], merge_dct[k])
        else:
            # Prefer original dict values over merged dict values if they already exist
            if k not in dct.keys():
                dct[k] = merge_dct[k]
    return dct


def refresh_dynamic_config(ddb=None):
    if not ddb:
        # This function runs frequently. We provide the option to pass in a UserDynamoHandler
        # so we don't need to import on every invocation
        from consoleme.lib.dynamo import UserDynamoHandler

        ddb = UserDynamoHandler()
    return ddb.get_dynamic_config_dict()


class Configuration(object):
    """Load YAML configuration files. YAML files can be extended to extend each other, to include common configuration
    values."""

    def __init__(self) -> None:
        """Initialize empty configuration."""
        self.config = {}
        self.log = None

    def load_config_from_dynamo(self):
        """If enabled, we can load a configuration dynamically from Dynamo at a certain time interval. This reduces
        the need for code redeploys to make configuration changes"""
        from consoleme.lib.dynamo import UserDynamoHandler
        from consoleme.lib.redis import RedisHandler

        ddb = UserDynamoHandler()
        red = RedisHandler().redis_sync()

        while True:
            dynamic_config = refresh_dynamic_config(ddb)
            if dynamic_config and dynamic_config != self.config.get("dynamic_config"):
                red.set(
                    "DYNAMIC_CONFIG_CACHE",
                    json.dumps(dynamic_config),
                )
                self.get_logger("config").debug(
                    {
                        "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
                        "message": "Dynamic configuration changes detected and loaded",
                        "dynamic_config": dynamic_config,
                    }
                )
                self.config["dynamic_config"] = dynamic_config
            time.sleep(self.get("dynamic_config.dynamo_load_interval", 60))

    def purge_redislite_cache(self):
        """
        Purges redislite cache in primary DB periodically. This will force a cache refresh, and it is
        convenient for cases where you cannot securely run shared Redis (ie: AWS AppRunner)
        """
        if not self.get("redis.use_redislite"):
            return
        from consoleme.lib.redis import RedisHandler

        red = RedisHandler().redis_sync()
        while True:
            red.flushdb()
            time.sleep(self.get("redis.purge_redislite_cache_interval", 1800))

    async def merge_extended_paths(self, extends, dir_path):
        for s in extends:
            extend_config = {}
            # This decode and YAML-load a string stored in AWS Secrets Manager
            if s.startswith("AWS_SECRETS_MANAGER:"):
                secret_name = "".join(s.split("AWS_SECRETS_MANAGER:")[1:])
                extend_config = yaml.safe_load(
                    get_aws_secret(
                        secret_name, os.environ.get("EC2_REGION", "us-east-1")
                    )
                )
            else:
                try:
                    extend_path = os.path.join(dir_path, s)
                    with open(extend_path, "r") as ymlfile:
                        extend_config = yaml.safe_load(ymlfile)
                except FileNotFoundError:
                    logging.error(f"Unable to open file: {s}", exc_info=True)

            dict_merge(self.config, extend_config)
            if extend_config.get("extends"):
                await self.merge_extended_paths(extend_config.get("extends"), dir_path)

    def reload_config(self):
        # We don't want to start additional background threads when we're reloading static configuration.
        while True:
            async_to_sync(self.load_config)(
                allow_automatically_reload_configuration=False,
                allow_start_background_threads=False,
            )
            if not self.get("config.automatically_reload_configuration"):
                break
            time.sleep(self.get("dynamic_config.reload_static_config_interval", 60))

    async def load_config(
        self,
        allow_automatically_reload_configuration=True,
        allow_start_background_threads=True,
    ):
        """Load configuration from the location given to us by config_plugin"""
        path = config_plugin.get_config_location()

        try:
            with open(path, "r") as ymlfile:
                self.config = yaml.safe_load(ymlfile)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                "File not found. Please set the CONFIG_LOCATION environmental variable "
                f"to point to ConsoleMe's YAML configuration file: {e}"
            )

        extends = self.get("extends")
        dir_path = os.path.dirname(path)

        if extends:
            await self.merge_extended_paths(extends, dir_path)

        if allow_start_background_threads and self.get("redis.use_redislite"):
            Timer(0, self.purge_redislite_cache, ()).start()

        if allow_start_background_threads and self.get("config.load_from_dynamo", True):
            Timer(0, self.load_config_from_dynamo, ()).start()

        if allow_start_background_threads and self.get(
            "config.run_recurring_internal_tasks"
        ):
            Timer(
                0, config_plugin.internal_functions, kwargs={"cfg": self.config}
            ).start()

        if allow_automatically_reload_configuration and self.get(
            "config.automatically_reload_configuration"
        ):
            Timer(0, self.reload_config, ()).start()

    def get(
        self, key: str, default: Optional[Union[List[str], int, bool, str, Dict]] = None
    ) -> Any:
        """Get value for configuration entry in dot notation."""
        value = self.config
        for k in key.split("."):
            try:
                value = value[k]
            except KeyError:
                return default
        return value

    def get_logger(self, name: Optional[str] = None) -> LoggerAdapter:
        """Get logger."""
        if self.log:
            return self.log
        if not name:
            name = self.get("application_name", "consoleme")
        level_c = self.get("logging.level", "debug")
        if level_c == "info":
            level = logging.INFO
        elif level_c == "critical":
            level = logging.CRITICAL
        elif level_c == "error":
            level = logging.ERROR
        elif level_c == "warning":
            level = logging.WARNING
        elif level_c == "debug":
            level = logging.DEBUG
        else:
            # default
            level = logging.DEBUG
        filter_c = ContextFilter()
        format_c = self.get(
            "logging.format",
            "%(asctime)s - %(levelname)s - %(name)s - [%(filename)s:%(lineno)s - %(funcName)s() ] - %(message)s",
        )

        logging.basicConfig(level=level, format=format_c)
        logger = logging.getLogger(name)
        logger.addFilter(filter_c)

        extra = {"eventTime": datetime.datetime.now(timezone("US/Pacific")).isoformat()}

        now = datetime.datetime.now()

        # Elasticsearch logging
        if self.get("logging.elasticsearch_enabled", False):
            try:
                es = f"{self.get('logging.elasticsearch.host')}:{self.get('logging.elasticsearch.port')}"
                index_name = (
                    f"{self.get('logging.elasticsearch.index_name', 'consoleme')}-'"
                    f"{now.year}{now.month}{now.day}"
                )
                from consoleme.lib.elasticsearch import ESHandler

                handler = ESHandler(es, index_name)
                handler.setFormatter(logmatic.JsonFormatter())
                handler.setLevel(self.get("logging.elasticsearch.level", "INFO"))
                logger.addHandler(handler)
            except Exception:
                logger.error(
                    "Unable to configure Elasticsearch logging.", exc_info=True
                )
        # Log to stdout and disk
        if self.get("logging.stdout_enabled", True):
            logger.propagate = False
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logmatic.JsonFormatter())
            handler.setLevel(self.get("logging.stdout.level", "DEBUG"))
            logger.addHandler(handler)
            logging_file = self.get("logging.file")
            if logging_file:
                if "~" in logging_file:
                    logging_file = os.path.expanduser(logging_file)
                os.makedirs(os.path.dirname(logging_file), exist_ok=True)
                file_handler = logging.FileHandler(logging_file)
                file_handler.setFormatter(logmatic.JsonFormatter())
                logger.addHandler(file_handler)
        self.log = logging.LoggerAdapter(logger, extra)
        return self.log

    def set_logging_levels(self):
        default_logging_levels = {
            "asyncio": "WARNING",
            "boto3": "CRITICAL",
            "boto": "CRITICAL",
            "botocore": "CRITICAL",
            "elasticsearch.trace": "ERROR",
            "elasticsearch": "ERROR",
            "nose": "CRITICAL",
            "parso.python.diff": "WARNING",
            "raven.base.client": "WARNING",
            "role_protect_client": "WARNING",
            "s3transfer": "CRITICAL",
            "spectator.HttpClient": "WARNING",
            "spectator.Registry": "WARNING",
            "urllib3": "ERROR",
            "redislite.client": "WARNING",
            "redislite.configuration": "WARNING",
        }
        for logger, level in self.get("logging_levels", default_logging_levels).items():
            logging.getLogger(logger).setLevel(level)

    def get_aws_region(self):
        region_checks = [
            # check if set through ENV vars
            os.environ.get("EC2_REGION"),
            os.environ.get("AWS_REGION"),
            os.environ.get("AWS_DEFAULT_REGION"),
            # else check if set in config or in boto already
            boto3.DEFAULT_SESSION.region_name if boto3.DEFAULT_SESSION else None,
            boto3.Session().region_name,
            boto3.client("s3").meta.region_name,
            "us-east-1",
        ]
        for region in region_checks:
            if region:
                return region


class ContextFilter(logging.Filter):
    """Logging Filter for adding hostname to log entries."""

    hostname = socket.gethostname()

    def filter(self, record: LogRecord) -> bool:
        record.hostname = ContextFilter.hostname
        return True


CONFIG = Configuration()
async_to_sync(CONFIG.load_config)()

get = CONFIG.get
get_logger = CONFIG.get_logger

# Set logging levels
CONFIG.set_logging_levels()

values = CONFIG.config
region = CONFIG.get_aws_region()
hostname = socket.gethostname()
api_spec = {}
dir_ref = dir

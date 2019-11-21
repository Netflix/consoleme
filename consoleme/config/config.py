"""Configuration handling library."""

import collections
import datetime
import logging
import os
import socket
import sys
import time
from logging import LogRecord, LoggerAdapter
from threading import Timer
from typing import Any, List, Optional, Union

import logmatic
import yaml
from asgiref.sync import async_to_sync
from pytz import timezone
from raven.contrib.tornado import AsyncSentryClient

from consoleme.lib.plugins import get_plugin_by_name

config_plugin_entrypoint = os.environ.get("CONSOLEME_CONFIG_ENTRYPOINT", "default_config")
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

        ddb = UserDynamoHandler()

        while True:
            dynamic_config = ddb.get_dynamic_config_dict()
            if dynamic_config != self.config.get("dynamic_config"):
                self.get_logger("config").debug(
                    {
                        "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
                        "message": "Dynamic configuration changes detected and loaded",
                        "dynamic_config": dynamic_config,
                    }
                )
                self.config["dynamic_config"] = dynamic_config
            time.sleep(self.get("dynamic_config.dynamo_load_interval", 60))

    async def load_config(self):
        """Load configuration from file referenced in config env variable CONFIG_LOCATION."""
        path = os.environ.get("CONFIG_LOCATION")
        if not path:
            path = config_plugin.get_config_location()
        with open(path, "r") as ymlfile:
            self.config = yaml.safe_load(ymlfile)

        extends = self.get("extends")
        dir_path = os.path.dirname(path)

        for s in extends:
            try:
                extend_path = os.path.join(dir_path, s)
                with open(extend_path, "r") as ymlfile:
                    extend_config = yaml.safe_load(ymlfile)
                dict_merge(self.config, extend_config)
            except FileNotFoundError:
                logging.error(f"Unable to open file: {s}", exc_info=True)

        if self.get("config.load_from_dynamo"):
            Timer(0, self.load_config_from_dynamo, ()).start()

        if self.get("config.run_recurring_internal_tasks"):
            Timer(
                0, config_plugin.internal_functions, kwargs={"cfg": self.config}
            ).start()

    def get(
        self, key: str, default: Optional[Union[List[str], int, bool, str]] = None
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
            name = self.get("application_name")
        level_c = self.get("logging.level")
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
        format_c = self.get("logging.format", "")

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
values = CONFIG.config
region = os.environ.get("EC2_REGION", "us-east-1")
hostname = socket.gethostname()
api_spec = {}
dir_ref = dir

sentry: AsyncSentryClient = AsyncSentryClient(get("sentry.dsn"))

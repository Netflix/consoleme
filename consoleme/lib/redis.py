import os
import sys
import threading
import time
from typing import Any, Optional

import boto3
import redis
import ujson as json
from asgiref.sync import sync_to_async
from redis.client import Redis

from consoleme.config import config
from consoleme.lib.plugins import get_plugin_by_name

if config.get("redis.use_redislite"):
    import tempfile

    import redislite

    if not config.get("redis.redis_lite.db_path"):
        default_redislite_db_path = tempfile.NamedTemporaryFile().name

region = config.region
log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()

automatically_backup_to_s3 = config.get(
    "redis.automatically_backup_to_s3.enabled", False
)
automatically_restore_from_s3 = config.get(
    "redis.automatically_restore_from_s3.enabled", False
)
s3 = boto3.resource("s3", **config.get("boto3.client_kwargs", {}))
s3_bucket = config.get("redis.automatically_backup_to_s3.bucket")
s3_folder = config.get("redis.automatically_backup_to_s3.folder")


# ToDo - Switch to Aioredis
class ConsoleMeRedis(redis.StrictRedis):
    """
    ConsoleMeRedis is a simple wrapper around redis.StrictRedis. It was created to allow Redis to be optional.
    If Redis settings are not defined in ConsoleMe's configuration, we "disable" redis. If Redis is disabled, calls to
    Redis will fail silently. If new Redis calls are added to ConsoleMe, they should be added to this class.

    ConsoleMeRedis also supports writing/retrieving data from S3 if the data is not retrievable from Redis
    """

    def __init__(self, *args, **kwargs):
        self.enabled = True
        if kwargs["host"] is None or kwargs["port"] is None or kwargs["db"] is None:
            self.enabled = False
        super(ConsoleMeRedis, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        if not self.enabled:
            return None
        try:
            result = super(ConsoleMeRedis, self).get(*args, **kwargs)
        except redis.exceptions.ConnectionError as e:
            function = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log.error(
                {
                    "function": function,
                    "message": "Unable to perform redis operation",
                    "key": args[0],
                    "error": e,
                },
                exc_info=True,
            )
            stats.count(f"{function}.error")
            result = None
        if not result and automatically_restore_from_s3:
            try:
                obj = s3.Object(s3_bucket, s3_folder + f"/{args[0]}")
                result = obj.get()["Body"].read().decode("utf-8")
            except s3.meta.client.exceptions.NoSuchKey:
                pass
            except Exception as e:
                function = f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
                log.error(
                    {
                        "function": function,
                        "message": "Unable to perform S3 operation",
                        "key": args[0],
                        "error": e,
                    },
                    exc_info=True,
                )
                stats.count(f"{function}.error")
        return result

    def set(self, *args, **kwargs):
        if not self.enabled:
            return False
        try:
            result = super(ConsoleMeRedis, self).set(*args, **kwargs)
        except redis.exceptions.ConnectionError as e:
            function = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log.error(
                {
                    "function": function,
                    "message": "Unable to perform redis operation",
                    "key": args[0],
                    "error": e,
                },
                exc_info=True,
            )
            stats.count(f"{function}.error")
            result = None
        if automatically_backup_to_s3:
            try:
                obj = s3.Object(s3_bucket, s3_folder + f"/{args[0]}")
                obj.put(Body=str(args[1]))
            except Exception as e:
                function = f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
                log.error(
                    {
                        "function": function,
                        "message": "Unable to perform S3 operation",
                        "key": args[0],
                        "error": e,
                    },
                    exc_info=True,
                )
                stats.count(f"{function}.error")
        return result

    def setex(self, *args, **kwargs):
        if not self.enabled:
            return False
        # We do not currently support caching data in S3 with expiration (SETEX)
        try:
            result = super(ConsoleMeRedis, self).setex(*args, **kwargs)
        except redis.exceptions.ConnectionError as e:
            function = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log.error(
                {
                    "function": function,
                    "message": "Unable to perform redis operation",
                    "key": args[0],
                    "error": e,
                },
                exc_info=True,
            )
            stats.count(f"{function}.error")
            result = None
        return result

    def hmset(self, *args, **kwargs):
        if not self.enabled:
            return False
        try:
            result = super(ConsoleMeRedis, self).hmset(*args, **kwargs)
        except redis.exceptions.ConnectionError as e:
            function = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log.error(
                {
                    "function": function,
                    "message": "Unable to perform redis operation",
                    "key": args[0],
                    "error": e,
                },
                exc_info=True,
            )
            stats.count(f"{function}.error")
            result = None
        if automatically_backup_to_s3:
            try:
                obj = s3.Object(s3_bucket, s3_folder + f"/{args[0]}")
                # Write to S3 in a separate thread
                t = threading.Thread(
                    target=obj.put, kwargs={"Body": json.dumps(args[1])}
                )
                t.daemon = True
                t.start()
            except Exception as e:
                function = f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
                log.error(
                    {
                        "function": function,
                        "message": "Unable to perform S3 operation",
                        "key": args[0],
                        "error": e,
                    },
                    exc_info=True,
                )
                stats.count(f"{function}.error")
        return result

    def hset(self, *args, **kwargs):
        if not self.enabled:
            return False
        try:
            result = super(ConsoleMeRedis, self).hset(*args, **kwargs)
        except redis.exceptions.ConnectionError as e:
            function = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log.error(
                {
                    "function": function,
                    "message": "Unable to perform redis operation",
                    "key": args[0],
                    "error": e,
                },
                exc_info=True,
            )
            stats.count(f"{function}.error")
            result = None
        if automatically_backup_to_s3:
            try:
                obj = s3.Object(s3_bucket, s3_folder + f"/{args[0]}")
                try:
                    current = json.loads(obj.get()["Body"].read().decode("utf-8"))
                    current[args[1]] = args[2]
                except:  # noqa
                    current = {args[1]: args[2]}
                t = threading.Thread(
                    target=obj.put, kwargs={"Body": json.dumps(current)}
                )
                t.daemon = True
                t.start()
            except Exception as e:
                function = f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
                log.error(
                    {
                        "function": function,
                        "message": "Unable to perform S3 operation",
                        "key": args[0],
                        "error": e,
                    },
                    exc_info=True,
                )
                stats.count(f"{function}.error")
        return result

    def hget(self, *args, **kwargs):
        if not self.enabled:
            return None
        try:
            result = super(ConsoleMeRedis, self).hget(*args, **kwargs)
        except redis.exceptions.ConnectionError as e:
            function = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log.error(
                {
                    "function": function,
                    "message": "Unable to perform redis operation",
                    "key": args[0],
                    "error": e,
                },
                exc_info=True,
            )
            stats.count(f"{function}.error")
            result = None

        if not result and automatically_restore_from_s3:
            try:
                obj = s3.Object(s3_bucket, s3_folder + f"/{args[0]}")
                current = json.loads(obj.get()["Body"].read().decode("utf-8"))
                result = current.get(args[1])
                if result:
                    self.hset(args[0], args[1], result)
            except s3.meta.client.exceptions.NoSuchKey:
                pass
            except Exception as e:
                function = f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
                log.error(
                    {
                        "function": function,
                        "message": "Unable to perform S3 operation",
                        "key": args[0],
                        "error": e,
                    },
                    exc_info=True,
                )
                stats.count(f"{function}.error")
        return result

    def hmget(self, *args, **kwargs):
        if not self.enabled:
            return None
        try:
            result = super(ConsoleMeRedis, self).hmget(*args, **kwargs)
        except redis.exceptions.ConnectionError as e:
            function = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log.error(
                {
                    "function": function,
                    "message": "Unable to perform redis operation",
                    "key": args[0],
                    "error": e,
                },
                exc_info=True,
            )
            stats.count(f"{function}.error")
            result = None
        return result

    def hgetall(self, *args, **kwargs):
        if not self.enabled:
            return None
        try:
            result = super(ConsoleMeRedis, self).hgetall(*args, **kwargs)
        except redis.exceptions.ConnectionError as e:
            function = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log.error(
                {
                    "function": function,
                    "message": "Unable to perform redis operation",
                    "key": args[0],
                    "error": e,
                },
                exc_info=True,
            )
            stats.count(f"{function}.error")
            result = None
        if not result and automatically_restore_from_s3:
            try:
                obj = s3.Object(s3_bucket, s3_folder + f"/{args[0]}")
                result_j = obj.get()["Body"].read().decode("utf-8")
                result = json.loads(result_j)
                if result:
                    self.hmset(args[0], result)
            except s3.meta.client.exceptions.NoSuchKey:
                pass
            except Exception as e:
                function = f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
                log.error(
                    {
                        "function": function,
                        "message": "Unable to perform S3 operation",
                        "key": args[0],
                        "error": e,
                    },
                    exc_info=True,
                )
                stats.count(f"{function}.error")
        return result


class RedisHandler:
    def __init__(
        self,
        host: str = config.get(
            "redis.host.{}".format(region), config.get("redis.host.global", "localhost")
        ),
        port: int = config.get("redis.port", 6379),
        db: int = config.get("redis.db", 0),
    ) -> None:
        self.red = None
        self.host = host
        self.port = port
        self.db = db
        self.enabled = True
        if self.host is None or self.port is None or self.db is None:
            self.enabled = False

    async def redis(self, db: int = 0) -> Redis:
        if config.get("redis.use_redislite"):
            REDIS_DB_PATH = os.path.join(
                config.get("redis.redislite.db_path", default_redislite_db_path)
            )
            return redislite.StrictRedis(REDIS_DB_PATH, decode_responses=True)
        self.red = await sync_to_async(ConsoleMeRedis)(
            host=self.host,
            port=self.port,
            db=self.db,
            charset="utf-8",
            decode_responses=True,
        )
        return self.red

    def redis_sync(self, db: int = 0) -> Redis:
        if config.get("redis.use_redislite"):
            REDIS_DB_PATH = os.path.join(
                config.get("redis.redislite.db_path", default_redislite_db_path)
            )
            return redislite.StrictRedis(REDIS_DB_PATH, decode_responses=True)
        self.red = ConsoleMeRedis(
            host=self.host,
            port=self.port,
            db=self.db,
            charset="utf-8",
            decode_responses=True,
        )
        return self.red


async def redis_get(key: str, default: Optional[str] = None) -> Optional[str]:
    red = await RedisHandler().redis()
    v = await sync_to_async(red.get)(key)
    if not v:
        return default
    return v


async def redis_hgetall(key: str, default=None):
    red = await RedisHandler().redis()
    v = await sync_to_async(red.hgetall)(key)
    if not v:
        return default
    return v


async def redis_hget(name: str, key: str, default=None):
    red = await RedisHandler().redis()
    v = await sync_to_async(red.hget)(name, key)
    if not v:
        return default
    return v


def redis_get_sync(key: str, default: None = None) -> Optional[str]:
    red = RedisHandler().redis_sync()
    try:
        v = red.get(key)
    except redis.exceptions.ConnectionError:
        v = None
    if not v:
        return default
    return v


async def redis_hsetex(name: str, key: str, value: Any, expiration_seconds: int):
    """
    Lazy way to set Redis hash keys with an expiration. Warning: Entries set here only get deleted when redis_hgetex
    is called on an expired key.

    :param name: Redis key
    :param key: Hash key
    :param value: Hash value
    :param expiration_seconds: Number of seconds to consider entry expired
    :return:
    """
    expiration = int(time.time()) + expiration_seconds
    red = await RedisHandler().redis()
    v = await sync_to_async(red.hset)(
        name, key, json.dumps({"value": value, "ttl": expiration})
    )
    return v


async def redis_hgetex(name: str, key: str, default=None):
    """
    Lazy way to retrieve an entry from a Redis Hash, and delete it if it's due to expire.

    :param name:
    :param key:
    :param default:
    :return:
    """
    red = await RedisHandler().redis()
    if not red.exists(name):
        return default
    result_j = await sync_to_async(red.hget)(name, key)
    if not result_j:
        return default
    result = json.loads(result_j)
    if int(time.time()) > result["ttl"]:
        red.hdel(name, key)
        return default
    return result["value"]

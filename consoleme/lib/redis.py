from typing import Optional

import redis
from asgiref.sync import sync_to_async
from redis.client import Redis

from consoleme.config import config

region = config.region


class RedisHandler:
    def __init__(
        self,
        host: str = config.get("redis.host.{}".format(region), "localhost"),
        port: int = config.get("redis.port", 6379),
        db: int = config.get("redis.db", 0),
    ) -> None:
        self.host = host
        self.port = port
        self.db = db

    async def redis(self, db: int = 0) -> Redis:
        red = await sync_to_async(redis.StrictRedis)(
            host=self.host,
            port=self.port,
            db=self.db,
            charset="utf-8",
            decode_responses=True,
        )
        return red

    def redis_sync(self, db: int = 0) -> Redis:
        red = redis.StrictRedis(
            host=self.host,
            port=self.port,
            db=self.db,
            charset="utf-8",
            decode_responses=True,
        )
        return red


async def redis_get(key: str, default: Optional[str] = None) -> str:
    red = await RedisHandler().redis()
    v = await sync_to_async(red.get)(key)
    if not v:
        return default
    return v


async def redis_hgetall(key, default=None):
    red = await RedisHandler().redis()
    v = await sync_to_async(red.hgetall)(key)
    if not v:
        return default
    return v


def redis_get_sync(key: str, default: None = None) -> str:
    red = RedisHandler().redis_sync()
    try:
        v = red.get(key)
    except redis.exceptions.ConnectionError:
        v = None
    if not v:
        return default
    return v

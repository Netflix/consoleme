import gzip
import json
import sys
import time
from typing import Any, Dict, List, Optional, Union

from asgiref.sync import sync_to_async

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    DataNotRetrievable,
    ExpiredData,
    UnsupportedRedisDataType,
)
from consoleme.lib.json_encoder import SetEncoder
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.redis import RedisHandler
from consoleme.lib.s3_helpers import get_object, put_object

red = RedisHandler().redis_sync()
stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()


async def store_json_results_in_redis_and_s3(
    data: Union[
        Dict[str, set],
        Dict[str, str],
        List[
            Union[
                Dict[str, Union[Union[str, int], Any]],
                Dict[str, Union[Union[str, None, int], Any]],
            ]
        ],
        str,
        Dict[str, list],
    ],
    redis_key: str = None,
    redis_data_type: str = "str",
    s3_bucket: str = None,
    s3_key: str = None,
    json_encoder=None,
):
    """
    Stores data in Redis and S3, depending on configuration

    :param redis_data_type: "str" or "hash", depending on how we're storing data in Redis
    :param data: Python dictionary or list that will be encoded in JSON for storage
    :param redis_key: Redis Key to store data to
    :param s3_bucket: S3 bucket to store data
    :param s3_key: S3 key to store data
    :return:
    """

    last_updated_redis_key = config.get(
        "store_json_results_in_redis_and_s3.last_updated_redis_key",
        "STORE_JSON_RESULTS_IN_REDIS_AND_S3_LAST_UPDATED",
    )

    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    last_updated = int(time.time())
    stats.count(
        f"{function}.called",
        tags={"redis_key": redis_key, "s3_bucket": s3_bucket, "s3_key": s3_key},
    )

    if redis_key:
        if redis_data_type == "str":
            if isinstance(data, str):
                red.set(redis_key, data)
            else:
                red.set(
                    redis_key, json.dumps(data, cls=SetEncoder, default=json_encoder)
                )
        elif redis_data_type == "hash":
            red.hmset(redis_key, data)
        else:
            raise UnsupportedRedisDataType("Unsupported redis_data_type passed")
        red.hset(last_updated_redis_key, redis_key, last_updated)

    if s3_bucket and s3_key:
        data_for_s3 = json.dumps(
            {"last_updated": last_updated, "data": data},
            cls=SetEncoder,
            default=json_encoder,
            indent=2,
        ).encode()
        if s3_key.endswith(".gz"):
            data_for_s3 = gzip.compress(data_for_s3)
        put_object(
            Bucket=s3_bucket,
            Key=s3_key,
            Body=data_for_s3,
        )


async def retrieve_json_data_from_redis_or_s3(
    redis_key: str = None,
    redis_data_type: str = "str",
    s3_bucket: str = None,
    s3_key: str = None,
    cache_to_redis_if_data_in_s3: bool = True,
    max_age: Optional[int] = None,
    default: Optional = None,
    json_object_hook: Optional = None,
    json_encoder: Optional = None,
):
    """
    Retrieve data from Redis as a priority. If data is unavailable in Redis, fall back to S3 and attempt to store
    data in Redis for quicker retrieval later.

    :param redis_data_type: "str" or "hash", depending on how the data is stored in Redis
    :param redis_key: Redis Key to retrieve data from
    :param s3_bucket: S3 bucket to retrieve data from
    :param s3_key: S3 key to retrieve data from
    :param cache_to_redis_if_data_in_s3: Cache the data in Redis if the data is in S3 but not Redis
    :return:
    """
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    last_updated_redis_key = config.get(
        "store_json_results_in_redis_and_s3.last_updated_redis_key",
        "STORE_JSON_RESULTS_IN_REDIS_AND_S3_LAST_UPDATED",
    )
    stats.count(
        f"{function}.called",
        tags={"redis_key": redis_key, "s3_bucket": s3_bucket, "s3_key": s3_key},
    )
    data = None
    if redis_key:
        if redis_data_type == "str":
            data_s = red.get(redis_key)
            if data_s:
                data = json.loads(data_s, object_hook=json_object_hook)
        elif redis_data_type == "hash":
            data = red.hgetall(redis_key)
        else:
            raise UnsupportedRedisDataType("Unsupported redis_data_type passed")
        if data and max_age:
            current_time = int(time.time())
            last_updated = int(red.hget(last_updated_redis_key, redis_key))
            if current_time - last_updated > max_age:
                raise ExpiredData(f"Data in Redis is older than {max_age} seconds.")

    # Fall back to S3 if there's no data
    if not data and s3_bucket and s3_key:
        s3_object = get_object(Bucket=s3_bucket, Key=s3_key)
        s3_object_content = await sync_to_async(s3_object["Body"].read)()
        if s3_key.endswith(".gz"):
            s3_object_content = gzip.decompress(s3_object_content)
        data_object = json.loads(s3_object_content, object_hook=json_object_hook)
        data = data_object["data"]

        if data and max_age:
            current_time = int(time.time())
            last_updated = data_object["last_updated"]
            if current_time - last_updated > max_age:
                raise ExpiredData(f"Data in S3 is older than {max_age} seconds.")
        if redis_key and cache_to_redis_if_data_in_s3:
            await store_json_results_in_redis_and_s3(
                data,
                redis_key=redis_key,
                redis_data_type=redis_data_type,
                json_encoder=json_encoder,
            )

    if data is not None:
        return data
    if default is not None:
        return default
    raise DataNotRetrievable("Unable to retrieve expected data.")

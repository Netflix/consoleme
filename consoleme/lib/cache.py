import json
import sys
import time
from typing import Dict, List, Union, Any

from consoleme.config import config
from consoleme.exceptions.exceptions import DataNotRetrievable, UnsupportedRedisDataType
from consoleme.lib.json_encoder import SetEncoder
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.redis import RedisHandler
from consoleme.lib.s3_helpers import get_object, put_object

red = RedisHandler().redis_sync()
stats = get_plugin_by_name(config.get("plugins.metrics"))()


def store_json_results_in_redis_and_s3(
    data: List[
        Union[
            Dict[str, Union[Union[str, int], Any]],
            Dict[str, Union[Union[str, None, int], Any]],
        ]
    ],
    redis_key: str = None,
    redis_data_type: str = "str",
    s3_bucket: str = None,
    s3_key: str = None,
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

    function = f"{__name__}.{sys._getframe().f_code.co_name}"

    stats.count(
        f"{function}.called",
        tags={"redis_key": redis_key, "s3_bucket": s3_bucket, "s3_key": s3_key},
    )

    if redis_key:
        if redis_data_type == "str":
            red.set(redis_key, json.dumps(data, cls=SetEncoder))
        elif redis_data_type == "hash":
            red.hmset(redis_key, data)
        else:
            raise UnsupportedRedisDataType("Unsupported redis_data_type passed")

    data_for_s3 = {"last_updated": int(time.time()), "data": data}

    if s3_bucket and s3_key:
        put_object(
            Bucket=s3_bucket,
            Key=s3_key,
            Body=json.dumps(data_for_s3, cls=SetEncoder, indent=2).encode(),
        )


def retrieve_json_data_from_redis_or_s3(
    redis_key: str = None,
    redis_data_type: str = "str",
    s3_bucket: str = None,
    s3_key: str = None,
    cache_to_redis_if_data_in_s3: bool = True,
):
    """
    Retrieve data from Redis as a priority. If data is unavailable in Redis, fall back to S3 and attempt to store
    data in Redis for quicker retrieval later

    :param redis_data_type: "str" or "hash", depending on how the data is stored in Redis
    :param redis_key: Redis Key to retrieve data from
    :param s3_bucket: S3 bucket to retrieve data from
    :param s3_key: S3 key to retrieve data from
    :param cache_to_redis_if_data_in_s3: Cache the data in Redis if the data is in S3 but not Redis
    :return:
    """
    function = f"{__name__}.{sys._getframe().f_code.co_name}"

    stats.count(
        f"{function}.called",
        tags={"redis_key": redis_key, "s3_bucket": s3_bucket, "s3_key": s3_key},
    )
    data = None
    if redis_data_type == "str":
        data_s = red.get(redis_key)
        if data_s:
            data = json.loads(data_s)
    elif redis_data_type == "hash":
        data = red.hgetall(redis_key)
    else:
        raise UnsupportedRedisDataType("Unsupported redis_data_type passed")

    # Fall back to S3 if there's no data
    if not data and s3_bucket and s3_key:
        data_object = get_object(Bucket=s3_bucket, Key=s3_key)
        data_object_content = data_object["Body"].read()
        data = json.loads(data_object_content)["data"]
        if redis_key and cache_to_redis_if_data_in_s3:
            store_json_results_in_redis_and_s3(
                data, redis_key=redis_key, redis_data_type=redis_data_type
            )

    if data is not None:
        return data
    raise DataNotRetrievable("Unable to retrieve expected data.")

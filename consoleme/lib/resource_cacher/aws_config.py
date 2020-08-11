import json  # We use a separate SetEncoder here so we cannot use ujson
import sys
from asgiref.sync import async_to_sync
from consoleme.config import config
from consoleme.lib.aws_config import aws_config
from consoleme.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from consoleme.lib.dynamo import UserDynamoHandler
from datetime import datetime, timedelta

log = config.get_logger()


def cache_resources_from_aws_config_for_account(account_id) -> dict:
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    s3_bucket = config.get("aws_config_cache.s3.bucket")
    s3_key = config.get("aws_config_cache.s3.file", "").format(account_id=account_id)
    dynamo = UserDynamoHandler()
    # Only query in active region, otherwise get data from DDB
    if config.region == config.get("celery.active_region") or config.get(
            "environment"
    ) in ["dev"]:
        results = aws_config.query(
            config.get(
                "cache_all_resources_from_aws_config.aws_config.all_resources_query",
                "select * where accountId = '{account_id}'",
            ).format(account_id=account_id),
            use_aggregator=False,
            account_id=account_id,
        )

        ttl: int = int((datetime.utcnow() + timedelta(hours=36)).timestamp())
        redis_result_set = {}
        for result in results:
            result["ttl"] = ttl
            if result.get("arn"):
                if redis_result_set.get(result["arn"]):
                    continue
                redis_result_set[result["arn"]] = json.dumps(result)

        async_to_sync(store_json_results_in_redis_and_s3)(
            redis_result_set,
            redis_key=config.get("aws_config_cache.redis_key"),
            redis_data_type="hash",
            s3_bucket=s3_bucket,
            s3_key=s3_key,
        )

        dynamo.write_resource_cache_data(results)
    else:
        redis_result_set = async_to_sync(retrieve_json_data_from_redis_or_s3)(
            s3_bucket=s3_bucket, s3_key=s3_key
        )

        async_to_sync(store_json_results_in_redis_and_s3)(
            redis_result_set,
            redis_key=config.get("aws_config_cache.redis_key"),
            redis_data_type="hash",
        )
    log_data = {
        "function": function,
        "account_id": account_id,
        "number_resources_synced": len(redis_result_set),
    }
    log.debug(log_data)
    return log_data

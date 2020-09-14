from typing import Optional

from asgiref.sync import async_to_sync, sync_to_async

from consoleme.config import config
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.lib.cache import retrieve_json_data_from_redis_or_s3
from consoleme.lib.redis import RedisHandler
from consoleme.models import ArnArray

red = async_to_sync(RedisHandler().redis)()


class ResourceTypeAheadHandlerV2(BaseAPIV2Handler):
    async def get(self):
        try:
            type_ahead: Optional[str] = (
                self.request.arguments.get("typeahead")[0].decode("utf-8").lower()
            )
        except TypeError:
            type_ahead = None

        try:
            account_id: Optional[str] = self.request.arguments.get("account_id")[
                0
            ].decode("utf-8")
        except TypeError:
            account_id = None

        try:
            resource_type: Optional[str] = self.request.arguments.get("resource_type")[
                0
            ].decode("utf-8")
        except TypeError:
            resource_type = None

        try:
            region: Optional[str] = self.request.arguments.get("region")[0].decode(
                "utf-8"
            )
        except TypeError:
            region = None

        try:
            limit: int = self.request.arguments.get("limit")[0].decode("utf-8")
            if limit:
                limit = int(limit)
        except TypeError:
            limit = 20

        resource_redis_cache_key = config.get("aws_config_cache.redis_key")
        all_resource_arns = await sync_to_async(red.hkeys)(resource_redis_cache_key)
        # Fall back to DynamoDB or S3?
        if not all_resource_arns:
            s3_bucket = config.get("aws_config_cache_combined.s3.bucket")
            s3_key = config.get("aws_config_cache_combined.s3.file")
            all_resources = await retrieve_json_data_from_redis_or_s3(
                s3_bucket=s3_bucket, s3_key=s3_key
            )
            all_resource_arns = all_resources.keys()
            await sync_to_async(red.hset)(resource_redis_cache_key, all_resources)

        matching = set()
        for arn in all_resource_arns:
            if len(matching) >= limit:
                break
            # ARN format: 'arn:aws:sqs:us-east-1:123456789012:resource_name'
            if resource_type and resource_type != arn.split(":")[2]:
                continue
            if region and region != arn.split(":")[3]:
                continue
            if account_id and account_id != arn.split(":")[4]:
                continue
            if type_ahead and type_ahead in arn.lower():
                matching.add(arn)
            elif not type_ahead:
                # Oh, you want all the things do you?
                matching.add(arn)
        arn_array = ArnArray.parse_obj((list(matching)))
        self.write(arn_array.json())

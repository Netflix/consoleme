import sys
from datetime import datetime
from typing import Any, Dict, List, Union

import boto3
import pytz
import ujson as json
from asgiref.sync import sync_to_async
from botocore.exceptions import ClientError
from cloudaux import sts_conn
from cloudaux.aws.decorators import rate_limited
from cloudaux.aws.sts import boto3_cached_conn

from consoleme.config import config
from consoleme.lib.plugins import get_plugin_by_name

log = config.get_logger("consoleme")
stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()


async def is_object_older_than_seconds(
    bucket: str, key: str, older_than_seconds: int, s3_client=None
) -> bool:
    """
    This function checks if an S3 object is older than the specified number of seconds. if the object doesn't
    exist, this function will return True.
    """
    now = datetime.utcnow().replace(tzinfo=pytz.utc)
    if not s3_client:
        s3_client = boto3.client("s3")
    try:
        res = await sync_to_async(s3_client.head_object)(Bucket=bucket, Key=key)
    except ClientError as e:
        # If file is not found, we'll tell the user it's older than the specified time
        if e.response.get("Error", {}).get("Code") == "404":
            return True
        raise
    datetime_value = res["LastModified"]
    if (now - datetime_value).total_seconds() > older_than_seconds:
        return True
    return False


@rate_limited()
@sts_conn("s3")
def put_object(client=None, **kwargs):
    """Create an S3 object -- calls wrapped with CloudAux."""
    return client.put_object(**kwargs)


def get_object(**kwargs):
    client = kwargs.get("client")
    assume_role = kwargs.get("assume_role")
    if not client:
        if assume_role:
            client = boto3_cached_conn(
                "s3",
                account_number=kwargs.get("account_number"),
                assume_role=assume_role,
                session_name=kwargs.get("session_name", "ConsoleMe"),
                region=kwargs.get("region", config.region),
            )
        else:
            client = boto3.client("s3")
    return client.get_object(Bucket=kwargs.get("Bucket"), Key=kwargs.get("Key"))


async def get_object_async(**kwargs):
    """Get an S3 object Asynchronously"""
    return await sync_to_async(get_object)(**kwargs)


async def fetch_json_object_from_s3(
    bucket: str, object: str
) -> Union[Dict[str, Any], List[dict]]:
    """
    Fetch and load a JSON-formatted object in S3
    :param bucket: S3 bucket
    :param object: S3 Object
    :return: Dict
    """
    s3_object = await get_object_async(Bucket=bucket, Key=object, region=config.region)
    object_content = s3_object["Body"].read()
    data = json.loads(object_content)
    return data


def map_operation_to_api(operation, default):
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    operations_map = {
        "BATCH.DELETE.OBJECT": "s3:DeleteObject",
        "REST.COPY.OBJECT": "s3:PutObject",
        "REST.COPY.OBJECT_GET": "REST.COPY.OBJECT_GET",
        "REST.COPY.PART": "s3:PutObject",
        "REST.DELETE.OBJECT": "s3:DeleteObject",
        "REST.DELETE.UPLOAD": "s3:DeleteObject",
        "REST.GET.ACCELERATE": "s3:GetAccelerateConfiguration",
        "REST.GET.ACL": "s3:GetObjectVersionAcl",
        "REST.GET.ANALYTICS": "s3:GetAnalyticsConfiguration",
        "REST.GET.BUCKET": "s3:GetBucket",
        "REST.GET.BUCKETPOLICY": "s3:GetBucketPolicy",
        "REST.GET.BUCKETVERSIONS": "s3:GetBucketVersioning",
        "REST.GET.CORS": "s3:GetBucketCORS",
        "REST.GET.ENCRYPTION": "s3:GetEncryptionConfiguration",
        "REST.GET.INTELLIGENT_TIERING": "REST.GET.INTELLIGENT_TIERING",
        "REST.GET.INVENTORY": "s3:GetInventoryConfiguration",
        "REST.GET.LIFECYCLE": "s3:GetLifecycleConfiguration",
        "REST.GET.LOCATION": "s3:GetBucketLocation",
        "REST.GET.LOGGING_STATUS": "s3:GetBucketLogging",
        "REST.GET.METRICS": "s3:GetMetricsConfiguration",
        "REST.GET.NOTIFICATION": "s3:GetBucketNotification",
        "REST.GET.OBJECT": "s3:GetObject",
        "REST.GET.OBJECT_LOCK_CONFIGURATION": "s3:GetObjectLockConfiguration",
        "REST.GET.OBJECT_TAGGING": "s3:GetObjectTagging",
        "REST.GET.POLICY_STATUS": "s3:GetBucketPolicyStatus",
        "REST.GET.PUBLIC_ACCESS_BLOCK": "s3:GetBucketPublicAccessBlock",
        "REST.GET.REPLICATION": "s3:GetReplicationConfiguration",
        "REST.GET.REQUEST_PAYMENT": "s3:GetBucketRequestPayment",
        "REST.GET.TAGGING": "s3:GetBucketTagging",
        "REST.GET.UPLOAD": "s3:GetObject",
        "REST.GET.UPLOADS": "s3:GetObject",
        "REST.GET.VERSIONING": "s3:GetObjectVersion",
        "REST.GET.WEBSITE": "s3:GetBucketWebsite",
        "REST.HEAD.BUCKET": "s3:ListBucket",
        "REST.HEAD.OBJECT": "s3:GetObject",
        "REST.COPY.PART_GET": "s3:GetObject",
        "REST.POST.BUCKET": "REST.POST.BUCKET",
        "REST.POST.MULTI_OBJECT_DELETE": "s3:DeleteObject",
        "REST.POST.RESTORE": "s3:RestoreObject",
        "REST.POST.UPLOAD": "s3:PutObject",
        "REST.POST.UPLOADS": "s3:PutObject",
        "REST.PUT.ACL": "s3:PutBucketAcl|s3:PutObjectAcl",
        "REST.PUT.BUCKET": "REST.PUT.BUCKET",
        "REST.PUT.BUCKETPOLICY": "s3:PutBucketPolicy",
        "REST.PUT.CORS": "s3:PutBucketCORS",
        "REST.PUT.LIFECYCLE": "s3:PutLifecycleConfiguration",
        "REST.PUT.LOGGING_STATUS": "REST.PUT.LOGGING_STATUS-NotBucketOwnerOrGrantee",
        "REST.PUT.NOTIFICATION": "s3:PutBucketNotification",
        "REST.PUT.OBJECT": "s3:PutObject",
        "REST.PUT.OBJECT_TAGGING": "s3:PutObjectTagging",
        "REST.PUT.PART": "s3:PutObject",
        "REST.PUT.PUBLIC_ACCESS_BLOCK": "s3:PutBucketPublicAccessBlock",
    }
    api_call = operations_map.get(operation)
    if api_call is None:
        stats.count(f"{function}.error")
        log.error(
            {
                "message": "S3 Operation Needs Mapping",
                "function": function,
                "query": operation,
            }
        )
        return default
    else:
        stats.count(f"{function}.success")
        return api_call

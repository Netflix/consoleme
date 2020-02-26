import sys

from consoleme.config import config
from consoleme.lib.plugins import get_plugin_by_name

log = config.get_logger("consoleme")
stats = get_plugin_by_name(config.get("plugins.metrics"))()


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
    api_call = operations_map.get(operation, None)
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

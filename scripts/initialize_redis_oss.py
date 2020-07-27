from consoleme.celery import celery_tasks as celery
from consoleme_default_plugins.plugins.celery_tasks import (
    celery_tasks as default_celery_tasks,
)

# Initialize Redis with an appropriate cache
# Must have S3 permissions to access Template list.

celery.cache_roles_across_accounts()
celery.cache_s3_buckets_across_accounts()
celery.cache_sns_topics_across_accounts()
celery.cache_sqs_queues_across_accounts()
celery.cache_policies_table_details()
celery.cache_managed_policies_across_accounts()
default_celery_tasks.cache_aws_account_information()
default_celery_tasks.cache_application_information()
celery.cache_resources_from_aws_config_across_accounts()
celery.cache_policies_table_details.apply_async(countdown=180)
print("DONE")

from consoleme.celery import celery_tasks as celery

# Initialize Redis with an appropriate cache
# Must have S3 permissions to access Template list.

celery.cache_roles_across_accounts()
celery.cache_s3_buckets_across_accounts()
celery.cache_sns_topics_across_accounts()
celery.cache_sqs_queues_across_accounts()
celery.cache_policies_table_details()
celery.cache_managed_policies_across_accounts()
celery.cache_policy_requests()
print("DONE")

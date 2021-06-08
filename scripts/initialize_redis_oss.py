import argparse

from asgiref.sync import async_to_sync

from consoleme.celery_tasks import celery_tasks as celery
from consoleme.lib.account_indexers import get_account_id_to_name_mapping
from consoleme_default_plugins.plugins.celery_tasks import (
    celery_tasks as default_celery_tasks,
)


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


parser = argparse.ArgumentParser(description="Populate ConsoleMe's Redis Cache")
parser.add_argument(
    "--use_celery",
    default=False,
    type=str2bool,
    help="Invoke celery tasks instead of running synchronously",
)
args = parser.parse_args()

if args.use_celery:
    # Initialize Redis locally. If use_celery is set to `True`, you must be running a celery beat and worker. You can
    # run this locally with the following command:
    # `celery -A consoleme.celery_tasks.celery_tasks worker -l DEBUG -B -E --concurrency=8`

    celery.cache_roles_across_accounts()
    celery.cache_s3_buckets_across_accounts()
    celery.cache_sns_topics_across_accounts()
    celery.cache_sqs_queues_across_accounts()
    celery.cache_managed_policies_across_accounts()
    default_celery_tasks.cache_application_information()
    celery.cache_resources_from_aws_config_across_accounts()
    celery.cache_policies_table_details.apply_async(countdown=180)
    celery.cache_policy_requests()
    celery.cache_credential_authorization_mapping.apply_async(countdown=180)

else:
    celery.cache_cloud_account_mapping()
    accounts_d = async_to_sync(get_account_id_to_name_mapping)()
    default_celery_tasks.cache_application_information()

    for account_id in accounts_d.keys():
        celery.cache_roles_for_account(account_id)
        celery.cache_s3_buckets_for_account(account_id)
        celery.cache_sns_topics_for_account(account_id)
        celery.cache_sqs_queues_for_account(account_id)
        celery.cache_managed_policies_for_account(account_id)
        celery.cache_resources_from_aws_config_for_account(account_id)
    celery.cache_policies_table_details()
    celery.cache_policy_requests()
    celery.cache_credential_authorization_mapping()
    # Forces writing config to S3
    celery.cache_roles_across_accounts(wait_for_subtask_completion=False)

print("Done caching redis data")

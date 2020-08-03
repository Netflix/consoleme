from consoleme.config import config
from consoleme.lib.account_indexers.aws_organizations import (
    retrieve_accounts_from_aws_organizations,
)
from consoleme.lib.account_indexers.local_config import retrieve_accounts_from_config
from consoleme.lib.account_indexers.swag import retrieve_accounts_from_swag
from consoleme.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.models import CloudAccountModelArray

ALL_IAM_MANAGED_POLICIES: dict = {}
ALL_IAM_MANAGED_POLICIES_LAST_UPDATE: int = 0

log = config.get_logger(__name__)
auth = get_plugin_by_name(config.get("plugins.auth"))()
stats = get_plugin_by_name(config.get("plugins.metrics"))()


async def cache_cloud_accounts() -> CloudAccountModelArray:
    """
    Gets Cloud Account Information from either ConsoleMe's configuration, AWS Organizations, or Swag,
    depending on configuration
    :return:
    """
    account_mapping = None
    # Get the accounts
    if config.get("cache_cloud_accounts.from_aws_organizations"):
        account_mapping = await retrieve_accounts_from_aws_organizations()
    elif config.get("cache_cloud_accounts.from_swag"):
        account_mapping = await retrieve_accounts_from_swag()
    elif config.get("cache_cloud_accounts.from_config", True):
        account_mapping = await retrieve_accounts_from_config()

    account_id_to_name = {}

    for account in account_mapping.accounts:
        account_id_to_name[account.id] = account.name

    redis_key = config.get(
        "cache_cloud_accounts.redis.key.all_accounts_key", "ALL_AWS_ACCOUNTS"
    )

    s3_bucket = None
    s3_key = None
    if config.region == config.get("celery.active_region") or config.get(
        "environment"
    ) in ["dev", "test"]:
        s3_bucket = config.get("cache_cloud_accounts.s3.bucket")
        s3_key = config.get("cache_cloud_accounts.s3.file")
    # Store full mapping of the model
    await store_json_results_in_redis_and_s3(
        account_mapping.json(), redis_key=redis_key, s3_bucket=s3_bucket, s3_key=s3_key
    )
    # Store Account ID to Account Name mapping
    redis_key = config.get(
        "cache_cloud_accounts.redis.key.account_id_to_name_key",
        "ACCOUNT_ID_TO_NAME_MAPPING",
    )
    await store_json_results_in_redis_and_s3(account_id_to_name, redis_key=redis_key)

    return account_mapping


async def get_account_id_to_name_mapping(status="active"):
    redis_key = config.get(
        "cache_cloud_accounts.redis.key.all_accounts_key", "ALL_AWS_ACCOUNTS"
    )
    accounts = await retrieve_json_data_from_redis_or_s3(redis_key, default=[])
    if not accounts:
        # Force a re-sync and then retry
        await cache_cloud_accounts()
        accounts = await retrieve_json_data_from_redis_or_s3(redis_key, default=[])

    account_id_to_name = {}
    for account in accounts.get("accounts", []):
        if status and account.get("status") != status:
            continue
        account_id_to_name[account["id"]] = account["name"]
    return account_id_to_name

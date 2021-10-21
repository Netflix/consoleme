import ujson as json

from consoleme.config import config
from consoleme.lib.account_indexers.aws_organizations import (
    retrieve_accounts_from_aws_organizations,
)
from consoleme.lib.account_indexers.current_account import retrieve_current_account
from consoleme.lib.account_indexers.local_config import retrieve_accounts_from_config
from consoleme.lib.account_indexers.swag import retrieve_accounts_from_swag
from consoleme.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.models import CloudAccountModelArray

log = config.get_logger(__name__)
auth = get_plugin_by_name(config.get("plugins.auth", "default_auth"))()
stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()


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

    if not account_mapping or not account_mapping.accounts:
        account_mapping = await retrieve_current_account()

    account_id_to_name = {}

    for account in account_mapping.accounts:
        account_id_to_name[account.id] = account.name

    redis_key = config.get(
        "cache_cloud_accounts.redis.key.all_accounts_key", "ALL_AWS_ACCOUNTS"
    )

    s3_bucket = None
    s3_key = None
    if config.region == config.get("celery.active_region", config.region) or config.get(
        "environment"
    ) in ["dev", "test"]:
        s3_bucket = config.get("cache_cloud_accounts.s3.bucket")
        s3_key = config.get(
            "cache_cloud_accounts.s3.file", "cache_cloud_accounts/accounts_v1.json.gz"
        )
    # Store full mapping of the model
    # We want to pass a dict to store_json_results_in_redis_and_s3, but the problem is account_mapping.dict()
    # includes pydantic objects that cannot be dumped to json without passing a special JSON encoder for the
    # Pydantic type, hence the usage of json.loads(account_mapping.json())
    await store_json_results_in_redis_and_s3(
        json.loads(account_mapping.json()),
        redis_key=redis_key,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
    )

    return account_mapping


async def get_cloud_account_model_array(
    status="active", environment=None, force_sync=False
):
    redis_key = config.get(
        "cache_cloud_accounts.redis.key.all_accounts_key", "ALL_AWS_ACCOUNTS"
    )
    accounts = await retrieve_json_data_from_redis_or_s3(redis_key, default={})
    if force_sync or not accounts or not accounts.get("accounts"):
        # Force a re-sync and then retry
        await cache_cloud_accounts()
        accounts = await retrieve_json_data_from_redis_or_s3(redis_key, default={})
    all_accounts = CloudAccountModelArray.parse_obj(accounts)
    filtered_accounts = CloudAccountModelArray(accounts=[])
    for account in all_accounts.accounts:
        if status and account.status.value != status:
            continue
        if environment and not account.environment:
            # if we are looking to filter on environment, and account doesn't contain environment information
            continue
        if environment and account.environment.value != environment:
            continue
        filtered_accounts.accounts.append(account)
    return filtered_accounts


async def get_account_id_to_name_mapping(
    status="active", environment=None, force_sync=False
):
    redis_key = config.get(
        "cache_cloud_accounts.redis.key.all_accounts_key", "ALL_AWS_ACCOUNTS"
    )
    accounts = await retrieve_json_data_from_redis_or_s3(redis_key, default={})
    if force_sync or not accounts or not accounts.get("accounts"):
        # Force a re-sync and then retry
        await cache_cloud_accounts()
        accounts = await retrieve_json_data_from_redis_or_s3(
            redis_key,
            s3_bucket=config.get("cache_cloud_accounts.s3.bucket"),
            s3_key=config.get(
                "cache_cloud_accounts.s3.file",
                "cache_cloud_accounts/accounts_v1.json.gz",
            ),
            default={},
        )

    account_id_to_name = {}
    for account in accounts.get("accounts", []):
        if status and account.get("status") != status:
            continue
        if environment and account.get("environment") != environment:
            continue
        account_id_to_name[account["id"]] = account["name"]
    return account_id_to_name

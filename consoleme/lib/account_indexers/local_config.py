from consoleme.config import config
from consoleme.models import CloudAccountModel, CloudAccountModelArray


async def retrieve_accounts_from_config() -> CloudAccountModelArray:
    cloud_accounts = []
    accounts_in_configuration = config.get("dynamic_config.account_ids_to_name", {})
    accounts_in_configuration.update(config.get("account_ids_to_name", {}))
    for account_id, names in accounts_in_configuration.items():
        account_name = names
        # Legacy support for a list of account names (with aliases)
        if account_name and isinstance(account_name, list):
            account_name = account_name[0]
        cloud_accounts.append(
            CloudAccountModel(
                id=account_id,
                name=account_name,
                status="active",
                sync_enabled=True,
                type="aws",
            )
        )
    return CloudAccountModelArray(accounts=cloud_accounts)

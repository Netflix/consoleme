from consoleme.config import config
from consoleme.models import CloudAccountModel, CloudAccountModelArray


async def retrieve_accounts_from_config() -> CloudAccountModelArray:
    cloud_accounts = []
    for account_id, names in config.get("account_ids_to_name", {}).items():
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

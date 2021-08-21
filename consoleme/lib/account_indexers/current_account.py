import boto3

from consoleme.config import config
from consoleme.models import CloudAccountModel, CloudAccountModelArray


async def retrieve_current_account() -> CloudAccountModelArray:
    client = boto3.client("sts", **config.get("boto3.client_kwargs", {}))
    identity = client.get_caller_identity()
    account_aliases = boto3.client(
        "iam", **config.get("boto3.client_kwargs", {})
    ).list_account_aliases()["AccountAliases"]
    account_id = None
    if identity and identity.get("Account"):
        account_id = identity.get("Account")
    account_name = account_id

    if account_aliases:
        account_name = account_aliases[0]

    cloud_account = [
        CloudAccountModel(
            id=account_id,
            name=account_name,
            status="active",
            sync_enabled=True,
            type="aws",
        )
    ]
    return CloudAccountModelArray(accounts=cloud_account)

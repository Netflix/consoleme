from asgiref.sync import sync_to_async
from cloudaux.aws.sts import boto3_cached_conn
from consoleme.config import config
from consoleme.exceptions.exceptions import MissingConfigurationValue


async def retrieve_accounts_from_aws_organizations():
    """
    Polls AWS Organizations for our Account ID to Account Name mapping
    :param: redis_key: A redis key where we'll store account_id -> account_name mapping
            s3_bucket: Optional s3 bucket name in which to store account_id -> account_name mapping
            s3_key: Optional s3 key in which to store account_id -> account_name mapping
    :return: account_id to account_name mapping
    """

    organizations_master_account_id = config.get(
        "cache_accounts_from_aws_organizations.organizations_master_account_id")
    role_to_assume = config.get(
        "cache_accounts_from_aws_organizations.organizations_master_role_to_assume",
        config.get("policies.role_name")
    )
    if not organizations_master_account_id:
        raise MissingConfigurationValue(
            "Your AWS Organizations Master Account ID is not specified in configuration. "
            "Unable to sync accounts from "
            "AWS Organizations"
        )

    if not role_to_assume:
        raise MissingConfigurationValue(
            "ConsoleMe doesn't know what role to assume to retrieve account information "
            "from AWS Organizations. please set the appropriate configuration value."
        )
    client = await sync_to_async(boto3_cached_conn)(
        "organizations",
        account_number=organizations_master_account_id,
        assume_role=role_to_assume,
    )

    accounts = await sync_to_async(client.list_accounts)()

    account_id_to_name_mapping = {}
    for account in accounts.get("Accounts"):
        account_id_to_name_mapping[account["Id"]] = [account["Name"]]

    return account_id_to_name_mapping

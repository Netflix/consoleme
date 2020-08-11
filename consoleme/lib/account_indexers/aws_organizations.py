from asgiref.sync import sync_to_async
from cloudaux.aws.sts import boto3_cached_conn

from consoleme.config import config
from consoleme.exceptions.exceptions import MissingConfigurationValue
from consoleme.models import CloudAccountModel, CloudAccountModelArray


async def retrieve_accounts_from_aws_organizations() -> CloudAccountModelArray:
    """
    Polls AWS Organizations for our Account ID to Account Name mapping
    :param: null
    :return: CloudAccountModelArray
    """

    organizations_master_account_id = config.get(
        "cache_accounts_from_aws_organizations.organizations_master_account_id"
    )
    role_to_assume = config.get(
        "cache_accounts_from_aws_organizations.organizations_master_role_to_assume",
        config.get("policies.role_name"),
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
        session_name="ConsoleMeOrganizationsSync",
    )
    paginator = await sync_to_async(client.get_paginator)("list_accounts")
    page_iterator = await sync_to_async(paginator.paginate)()
    accounts = []
    for page in page_iterator:
        accounts.extend(page["Accounts"])

    cloud_accounts = []
    for account in accounts:
        status = account["Status"].lower()
        cloud_accounts.append(
            CloudAccountModel(
                id=account["Id"],
                name=account["Name"],
                email=account["Email"],
                status=status,
                type="aws",
                sync_enabled=True,  # TODO: Check for tag to disable sync?
            )
        )

    return CloudAccountModelArray(accounts=cloud_accounts)

from typing import Dict, List

from asgiref.sync import sync_to_async
from botocore.exceptions import ClientError
from cloudaux import CloudAux
from cloudaux.aws.decorators import paginated
from cloudaux.aws.sts import boto3_cached_conn

from consoleme.config import config
from consoleme.exceptions.exceptions import MissingConfigurationValue
from consoleme.models import (
    CloudAccountModel,
    CloudAccountModelArray,
    ServiceControlPolicyArrayModel,
    ServiceControlPolicyDetailsModel,
    ServiceControlPolicyModel,
    ServiceControlPolicyTargetModel,
)


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


@paginated(
    "Policies",
    response_pagination_marker="NextToken",
    request_pagination_marker="NextToken",
)
def _list_service_control_policies(ca: CloudAux, **kwargs) -> List[Dict]:
    """Return a complete list of service control policy metadata dicts from the paginated ListPolicies API call"""
    return ca.call(
        "organizations.client.list_policies",
        Filter="SERVICE_CONTROL_POLICY",
        MaxResults=20,
        **kwargs
    )


def _transform_organizations_policy_object(policy: Dict) -> Dict:
    """Transform a Policy object returned by an AWS Organizations API to a more convenient format"""
    transformed_policy = policy["PolicySummary"]
    transformed_policy["Content"] = policy["Content"]
    return transformed_policy


def _get_service_control_policy(ca: CloudAux, policy_id: str) -> Dict:
    """Retrieve metadata for an SCP by Id, transformed to convenient format. If not found, return an empty dict."""
    try:
        r = ca.call("organizations.client.describe_policy", PolicyId=policy_id)[
            "Policy"
        ]
        return _transform_organizations_policy_object(r)
    except ClientError as e:
        if (
            e.response["Error"]["Code"] == "400"
            and "PolicyNotFoundException" in e.response["Error"]["Message"]
        ):
            return {}
        raise e


def _get_service_control_policy_by_name(ca: CloudAux, scp_name: str) -> Dict:
    """Return True if an SCP with the specified name exists in this account"""
    scps = _list_service_control_policies(ca)
    scp_id = next((x["Id"] for x in scps if x["Name"] == scp_name), None)
    if scp_id is None:
        return {}
    return _get_service_control_policy(ca, scp_id)


@paginated(
    "Targets",
    response_pagination_marker="NextToken",
    request_pagination_marker="NextToken",
)
def _list_targets_for_policy(
    ca: CloudAux, scp_id: str, **kwargs
) -> List[Dict[str, str]]:
    """Return a complete list of target metadata dicts from the paginated ListTargetsForPolicy API call"""
    return ca.call(
        "organizations.client.list_targets_for_policy",
        PolicyId=scp_id,
        MaxResults=20,
        **kwargs
    )


async def retrieve_scps_for_organization(
    org_account_id: str, region: str = "us-east-1"
) -> ServiceControlPolicyArrayModel:
    """Return a ServiceControlPolicyArrayModel containing all SCPs for an organization"""
    conn_details = {
        "assume_role": config.get("policies.role_name"),
        "account_number": org_account_id,
        "session_name": "ConsoleMeSCPSync",
        "region": region,
    }
    ca = CloudAux(**conn_details)
    all_scp_metadata = _list_service_control_policies(ca)
    all_scp_objects = []
    for scp_metadata in all_scp_metadata:
        targets = _list_targets_for_policy(ca, scp_metadata["Id"])
        policy = _get_service_control_policy(ca, scp_metadata["Id"])
        target_models = [ServiceControlPolicyTargetModel(**t) for t in targets]
        scp_object = ServiceControlPolicyModel(
            targets=target_models,
            policy=ServiceControlPolicyDetailsModel(**policy),
        )
        all_scp_objects.append(scp_object)
    all_scps = ServiceControlPolicyArrayModel(__root__=all_scp_objects)
    return all_scps

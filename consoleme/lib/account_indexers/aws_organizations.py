from typing import Any, Dict, List, Literal

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

    cloud_accounts = []
    for organization in config.get("cache_accounts_from_aws_organizations", []):
        organizations_master_account_id = organization.get(
            "organizations_master_account_id"
        )
        role_to_assume = organization.get(
            "organizations_master_role_to_assume",
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
    """Return a complete list of service control policy metadata dicts from the paginated ListPolicies API call

    Args:
        ca: CloudAux instance
    """
    return ca.call(
        "organizations.client.list_policies",
        Filter="SERVICE_CONTROL_POLICY",
        MaxResults=20,
        **kwargs
    )


async def _transform_organizations_policy_object(policy: Dict) -> Dict:
    """Transform a Policy object returned by an AWS Organizations API to a more convenient format

    Args:
        policy: policy dict returned from organizations:DescribePolicy API
    """
    transformed_policy = policy["PolicySummary"]
    transformed_policy["Content"] = policy["Content"]
    return transformed_policy


async def _get_service_control_policy(ca: CloudAux, policy_id: str) -> Dict:
    """Retrieve metadata for an SCP by Id, transformed to convenient format. If not found, return an empty dict

    Args:
        ca: CloudAux instance
        policy_id: Service Control Policy ID
    """
    try:
        result = await sync_to_async(ca.call)(
            "organizations.client.describe_policy", PolicyId=policy_id
        )
    except ClientError as e:
        if (
            e.response["Error"]["Code"] == "400"
            and "PolicyNotFoundException" in e.response["Error"]["Message"]
        ):
            return {}
        raise e
    policy = result.get("Policy")
    return await _transform_organizations_policy_object(policy)


@paginated(
    "Targets",
    response_pagination_marker="NextToken",
    request_pagination_marker="NextToken",
)
def _list_targets_for_policy(
    ca: CloudAux, scp_id: str, **kwargs
) -> List[Dict[str, str]]:
    """Return a complete list of target metadata dicts from the paginated ListTargetsForPolicy API call

    Args:
        ca: CloudAux instance
        scp_id: service control policy ID
    """
    return ca.call(
        "organizations.client.list_targets_for_policy",
        PolicyId=scp_id,
        MaxResults=20,
        **kwargs
    )


def _describe_ou(ca: CloudAux, ou_id: str, **kwargs) -> Dict[str, str]:
    """Wrapper for organizations:DescribeOrganizationalUnit

    Args:
        ca: CloudAux instance
        ou_id: organizational unit ID
    """
    result = ca.call(
        "organizations.client.describe_organizational_unit",
        OrganizationalUnitId=ou_id,
        **kwargs
    )
    return result.get("OrganizationalUnit")


def _describe_account(ca: CloudAux, account_id: str, **kwargs) -> Dict[str, str]:
    """Wrapper for organizations:DescribeAccount

    Args:
        ca: CloudAux instance
        account_id: AWS account ID
    """
    result = ca.call(
        "organizations.client.describe_account", AccountId=account_id, **kwargs
    )
    return result.get("Account")


@paginated(
    "Children",
    response_pagination_marker="NextToken",
    request_pagination_marker="NextToken",
)
def _list_children_for_ou(
    ca: CloudAux,
    parent_id: str,
    child_type: Literal["ACCOUNT", "ORGANIZATIONAL_UNIT"],
    **kwargs
) -> List[Dict[str, Any]]:
    """Wrapper for organizations:ListChildren

    Args:
        ca: CloudAux instance
        parent_id: ID of organization root or organizational unit
        child_type: ACCOUNT or ORGANIZATIONAL_UNIT
    """
    return ca.call(
        "organizations.client.list_children",
        ChildType=child_type,
        ParentId=parent_id,
        **kwargs
    )


@paginated(
    "Roots",
    response_pagination_marker="NextToken",
    request_pagination_marker="NextToken",
)
def _list_org_roots(ca: CloudAux, **kwargs) -> List[Dict[str, Any]]:
    """Wrapper for organizations:ListRoots

    Args:
        ca: CloudAux instance
    """
    return ca.call("organizations.client.list_roots", **kwargs)


def _get_children_for_ou(ca: CloudAux, root_id: str) -> Dict[str, Any]:
    """Recursively build OU structure

    Args:
        ca: CloudAux instance
        root_id: ID of organization root or organizational unit
    """
    children: List[Dict[str, Any]] = []
    children.extend(_list_children_for_ou(ca, root_id, "ORGANIZATIONAL_UNIT"))
    children.extend(_list_children_for_ou(ca, root_id, "ACCOUNT"))
    for child in children:
        child["Parent"] = root_id
        if child["Type"] == "ORGANIZATIONAL_UNIT":
            child.update(_describe_ou(ca, child["Id"]))
            child["Children"] = _get_children_for_ou(ca, child["Id"])
        else:
            child.update(_describe_account(ca, child["Id"]))
    return children


async def retrieve_org_structure(
    org_account_id: str, role_to_assume: str = "ConsoleMe", region: str = "us-east-1"
) -> Dict[str, Any]:
    """Retrieve org roots then recursively build a dict of child OUs and accounts.

    This is a slow and expensive operation.

    Args:
        org_account_id: ID for AWS account containing org(s)
        region: AWS region
    """
    conn_details = {
        "assume_role": role_to_assume,
        "account_number": org_account_id,
        "session_name": "ConsoleMeSCPSync",
        "region": region,
        "client_kwargs": config.get("boto3.client_kwargs", {}),
    }
    ca = CloudAux(**conn_details)
    roots = _list_org_roots(ca)
    org_structure = {}
    for root in roots:
        root_id = root["Id"]
        root["Children"] = _get_children_for_ou(ca, root["Id"])
        org_structure[root_id] = root
    return org_structure


async def retrieve_scps_for_organization(
    org_account_id: str, role_to_assume: str = "ConsoleMe", region: str = "us-east-1"
) -> List[ServiceControlPolicyModel]:
    """Return a ServiceControlPolicyArrayModel containing all SCPs for an organization

    Args:
        org_account_id: ID for AWS account containing org(s)
        region: AWS region
    """
    conn_details = {
        "assume_role": role_to_assume,
        "account_number": org_account_id,
        "session_name": "ConsoleMeSCPSync",
        "region": region,
        "client_kwargs": config.get("boto3.client_kwargs", {}),
    }
    ca = CloudAux(**conn_details)
    all_scp_metadata = await sync_to_async(_list_service_control_policies)(ca)
    all_scp_objects = []
    for scp_metadata in all_scp_metadata:
        targets = await sync_to_async(_list_targets_for_policy)(ca, scp_metadata["Id"])
        policy = await _get_service_control_policy(ca, scp_metadata["Id"])
        target_models = [ServiceControlPolicyTargetModel(**t) for t in targets]
        scp_object = ServiceControlPolicyModel(
            targets=target_models,
            policy=ServiceControlPolicyDetailsModel(**policy),
        )
        all_scp_objects.append(scp_object.dict())
    return all_scp_objects

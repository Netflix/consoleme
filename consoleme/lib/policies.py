import base64
import re
import sys
import time
import urllib
from collections import defaultdict
from typing import Dict, List

import ujson as json
from asgiref.sync import sync_to_async
from botocore.exceptions import ClientError
from cloudaux.aws.sts import boto3_cached_conn
from deepdiff import DeepDiff
from policy_sentry.util.actions import get_service_from_action

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    InvalidRequestParameter,
    MissingConfigurationValue,
)
from consoleme.lib.auth import can_admin_policies
from consoleme.lib.aws import (
    get_region_from_arn,
    get_resource_account,
    get_resource_from_arn,
    get_service_from_arn,
)
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.role_updater.handler import update_role
from consoleme.lib.ses import (
    send_new_comment_notification,
    send_policy_request_status_update_v2,
)
from consoleme.models import ExtendedRequestModel, RequestStatus

log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()


async def invalid_characters_in_policy(policy_value):
    if not policy_value:
        return False
    if "<" in policy_value or ">" in policy_value:
        return True
    return False


def escape_json(code):
    escaped = re.sub(
        r"(?<=</)s(?=cript)", lambda m: f"\\u{ord(m.group(0)):04x}", code, flags=re.I
    )
    return escaped


async def parse_policy_change_request(
    user: str, arn: str, role: str, data_list: list
) -> dict:
    result: dict = {"status": "success"}

    function = f"{__name__}.{sys._getframe().f_code.co_name}"

    stats.count(function, tags={"user": user, "arn": arn, "role": role})

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "role": role,
        "data_list": data_list,
        "arn": arn,
        "message": "Incoming request",
    }

    log.debug(log_data)
    events: list = []

    for data in data_list:
        requester: str = user

        # Make sure the requester is only ever 64 chars with domain
        if len(requester) > 64:
            split_items: list = requester.split("@")
            requester: str = (
                split_items[0][: (64 - (len(split_items[-1]) + 1))]
                + "@"
                + split_items[-1]
            )

        event: dict = {
            "arn": arn,
            "inline_policies": [],
            "managed_policies": [],
            "requester": requester,
        }
        if data.get("value") and await invalid_characters_in_policy(data["value"]):
            result["status"] = "error"
            result["error"] = "Invalid characters were detected in the policy."
            log_data["message"] = result["error"]
            log.error(log_data)
            return result
        if data["type"] == "InlinePolicy":
            name = data["name"]
            value = data.get("value")
            if value:
                value = json.loads(value)
            log_data["message"] = "Update inline policy"
            log_data["policy_name"] = name
            log_data["policy_value"] = value
            log.debug(log_data)

            # Check if policy being updated is the same as existing policy.
            # Check if a new policy is being created, ensure that we don't overwrite another policy with same name
            for existing_policy in role["policy"]["RolePolicyList"]:
                if data.get("is_new") and existing_policy.get("PolicyName") == name:
                    result["status"] = "error"
                    result[
                        "error"
                    ] = "You cannot make or request a new policy that has the same name as an existing policy."
                    log_data["message"] = result["error"]
                    log.error(log_data)
                    return result
                if existing_policy.get("PolicyName") == name:
                    if existing_policy.get("PolicyDocument") == value:
                        result["status"] = "error"
                        result[
                            "error"
                        ] = "No changes were found between the updated and existing policy."
                        log_data["message"] = result["error"]
                        log.error(log_data)
                        return result

            action = data.get("action", "attach")

            entry = {"action": action, "policy_name": name}
            if value:
                entry["policy_document"] = value

            event["inline_policies"].append(entry)
            events.append(event)
        if data["type"] == "ManagedPolicy":
            policy_arn = data["arn"]
            action = data["action"]
            policy_name = data["name"]
            log_data["message"] = "Update managed policy"
            log_data["action"] = action
            log_data["policy_arn"] = policy_arn
            log.debug(log_data)

            entry: dict = {"action": action, "arn": policy_arn}
            if action == "detach":
                seen = False
                for policy in role["policy"]["AttachedManagedPolicies"]:
                    if policy["PolicyName"] == policy_name:
                        seen = True
                        break
                if not seen:
                    result["status"] = "error"
                    result["error"] = (
                        f"There is no policy attached to role {arn} "
                        f"with arn {policy_arn} that can be removed."
                    )
                    log_data["message"] = result["error"]
                    log.error(log_data)
                    return result
                event["managed_policies"].append(entry)
                events.append(event)
            elif action == "attach":
                for policy in role["policy"]["AttachedManagedPolicies"]:
                    if policy["PolicyName"] == policy_name:
                        result["status"] = "error"
                        result["error"] = (
                            f"There is already a policy attached to role {arn} "
                            f"with arn {policy_arn}."
                        )
                        log_data["message"] = result["error"]
                        log.error(log_data)
                        return result
                event["managed_policies"].append(entry)
                events.append(event)

        elif data["type"] == "AssumeRolePolicyDocument":
            action = "update"
            value = json.loads(data["value"])
            log_data["message"] = "Update AssumeRolePolicyDocument"
            log_data["policy_value"] = data["value"]
            log.debug(log_data)

            # Check if policy being updated is the same as existing policy
            if role["policy"].get("AssumeRolePolicyDocument") == value:
                result["status"] = "error"
                result[
                    "error"
                ] = "No changes were found between the updated and existing assume role policy document."
                log_data["message"] = result["error"]
                log.error(log_data)
                return result

            # Todo(ccastrapel): Validate AWS syntax

            event["assume_role_policy_document"] = {
                "action": action,
                "assume_role_policy_document": value,
            }
            events.append(event)

        elif data["type"] == "delete_tag":
            action = "remove"
            key = data["name"]
            event["tags"] = [{"action": action, "key": key}]
            events.append(event)

        elif data["type"] == "update_tag":
            action = "add"
            key = data["name"]
            value = data["value"]
            event["tags"] = [{"action": action, "key": key, "value": value}]
            events.append(event)
    result["events"] = events
    return result


async def can_move_back_to_pending(request, current_user, groups):
    if request.get("status") in ["cancelled", "rejected"]:
        # Don't allow returning requests to pending state if more than a day has passed since the last update
        if request.get("last_updated", 0) < int(time.time()) - 86400:
            return False
        # Allow admins to return requests back to pending state
        if can_admin_policies(current_user, groups):
            return True
    return False


async def can_move_back_to_pending_v2(
    extended_request: ExtendedRequestModel, last_updated, current_user, groups
):
    if extended_request.request_status in [
        RequestStatus.cancelled,
        RequestStatus.rejected,
    ]:
        # Don't allow returning requests to pending state if more than a day has passed since the last update
        if last_updated < int(time.time()) - 86400:
            return False
        # Allow admins to return requests back to pending state
        if can_admin_policies(current_user, groups):
            return True
    return False


async def can_update_requests(request, user, groups):
    # Users can update their own requests
    can_update = user in request["username"]

    # Allow admins to return requests back to pending state
    if not can_update:
        if can_admin_policies(user, groups):
            return True

    return can_update


async def can_update_cancel_requests_v2(requester_username, user, groups):
    # Users can update their own requests
    can_update = user == requester_username

    # Allow admins to update / cancel requests
    if not can_update:
        if can_admin_policies(user, groups):
            return True

    return can_update


async def update_resource_policy(
    arn: str,
    resource_type: str,
    account_id: str,
    region: str,
    policy_changes: dict,
    resource_details: dict,
):
    # TODO: Prevent race conditions by ensuring policy hasn't been changed since user loaded existing policy
    function = f"{__name__}.{sys._getframe().f_code.co_name}"

    stats.count(
        function,
        tags={
            "arn": arn,
            "resource_type": resource_type,
            "account_id": account_id,
            "region": region,
        },
    )

    log_data = {
        "function": function,
        "arn": arn,
        "resource_type": resource_type,
        "account_id": account_id,
        "region": region,
        "policy_changes": policy_changes,
        "resource_details": resource_details,
    }

    log.debug(log_data)

    result = {"status": "success"}

    client = await sync_to_async(boto3_cached_conn)(
        resource_type,
        service_type="client",
        future_expiration_minutes=15,
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        region=region or config.region,
        session_name="ConsoleMe",
        arn_partition="aws",
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
    )

    resource = await sync_to_async(boto3_cached_conn)(
        resource_type,
        service_type="resource",
        future_expiration_minutes=15,
        account_number=account_id,
        assume_role=config.get("policies.role_name"),
        region=region or config.region,
        session_name="ConsoleMe",
        arn_partition="aws",
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
    )

    changes: bool = False

    resource_name: str = arn.split(":")[5]
    for change in policy_changes:
        try:
            if change.get("type") == "ResourcePolicy":
                proposed_policy = change["value"]
                changes = True
                if resource_details.get("Policy"):
                    if json.loads(proposed_policy) == resource_details["Policy"]:
                        result = {
                            "status": "error",
                            "message": "No changes were found between the updated and existing policy.",
                        }
                        return result
                if resource_type == "s3":
                    await sync_to_async(client.put_bucket_policy)(
                        Bucket=resource_name, Policy=proposed_policy
                    )
                elif resource_type == "sqs":
                    queue = await sync_to_async(resource.get_queue_by_name)(
                        QueueName=resource_name
                    )
                    await sync_to_async(queue.set_attributes)(
                        Attributes={"Policy": proposed_policy}
                    )
                elif resource_type == "sns":
                    topic = await sync_to_async(resource.Topic)(arn)
                    await sync_to_async(topic.set_attributes)(
                        AttributeName="Policy", AttributeValue=proposed_policy
                    )
            elif change.get("type") == "update_tag":
                changes = True
                if resource_type == "s3":
                    resource_details["TagSet"].append(
                        {"Key": change["name"], "Value": change["value"]}
                    )
                    await sync_to_async(client.put_bucket_tagging)(
                        Bucket=resource_name,
                        Tagging={"TagSet": resource_details["TagSet"]},
                    )
                elif resource_type == "sqs":
                    await sync_to_async(client.tag_queue)(
                        QueueUrl=resource_details["QueueUrl"],
                        Tags={change["name"]: change["value"]},
                    )
                elif resource_type == "sns":
                    await sync_to_async(client.tag_resource)(
                        ResourceArn=resource_details["TopicArn"],
                        Tags=[{"Key": change["name"], "Value": change["value"]}],
                    )
            elif change.get("type") == "delete_tag":
                changes = True
                if resource_type == "s3":
                    resulting_tagset = []

                    for tag in resource_details["TagSet"]:
                        if tag.get("Key") != change["name"]:
                            resulting_tagset.append(tag)

                    resource_details["TagSet"] = resulting_tagset
                    await sync_to_async(client.put_bucket_tagging)(
                        Bucket=resource_name,
                        Tagging={"TagSet": resource_details["TagSet"]},
                    )
                elif resource_type == "sqs":
                    await sync_to_async(client.untag_queue)(
                        QueueUrl=resource_details["QueueUrl"], TagKeys=[change["name"]]
                    )
                elif resource_type == "sns":
                    await sync_to_async(client.untag_resource)(
                        ResourceArn=resource_details["TopicArn"],
                        TagKeys=[change["name"]],
                    )
        except ClientError as e:
            log_data["message"] = "Error"
            log_data["error"] = e
            log.error(log_data, exc_info=True)
            result["status"] = "error"
            result["error"] = str(e)
            return result
    if not changes:
        result = {"status": "error", "message": "No changes detected."}
        return result
    return result


async def update_role_policy(events):
    result = {"status": "success"}

    function = f"{__name__}.{sys._getframe().f_code.co_name}"

    stats.count(function)

    log_data = {"function": function, "message": "Updating role policy"}

    response = await update_role(events)
    log_data["message"] = "Received Response"
    log_data["response"] = response
    log.debug(log_data)

    if not response.get("success"):
        log_data["message"] = "Error"
        log_data["error"] = response.get("message")
        log.error(log_data)
        result["status"] = "error"
        result["error"] = log_data["error"]
        return result

    return result


async def get_policy_request_uri(request):
    return f"{config.get('url')}/policies/request/{request['request_id']}"


async def get_policy_request_uri_v2(extended_request: ExtendedRequestModel):
    return f"{config.get('url')}/policies/request/{extended_request.id}"


async def validate_policy_name(policy_name):
    p = re.compile("^[a-zA-Z0-9+=,.@\\-_]+$")
    match = p.match(policy_name)
    if not match:
        raise InvalidRequestParameter(
            "The specified value for policyName is invalid. "
            "It must contain only alphanumeric characters and/or the following: +=,.@_-"
        )


async def get_resources_from_events(policy_changes: List[Dict]) -> Dict[str, dict]:
    """Returns a dict of resources affected by a list of policy changes along with
    the actions and other data points that are relevant to them.

    Returned dict format:
    {
        "resource_name": {
            "actions": ["service1:action1", "service2:action2"],
            "arns": ["arn:aws:service1:::resource_name", "arn:aws:service1:::resource_name/*"],
            "account": "1234567890",
            "type": "service1",
            "region": "",
        }
    }
    """

    def default_resource():
        return {"actions": [], "arns": [], "account": "", "type": "", "region": ""}

    resource_actions: Dict[str, Dict] = defaultdict(default_resource)
    for event in policy_changes:
        for policy_type in ["inline_policies", "managed_policies"]:
            for policy in event.get(policy_type, []):
                policy_document = policy["policy_document"]
                for statement in policy_document.get("Statement", []):
                    resources = statement.get("Resource", [])
                    resources = (
                        resources if isinstance(resources, list) else [resources]
                    )
                    for resource in resources:
                        if resource == "*":
                            continue
                        resource_name = get_resource_from_arn(resource)
                        if resource_name == "*":
                            continue
                        if not resource_actions[resource_name]["account"]:
                            resource_actions[resource_name][
                                "account"
                            ] = await get_resource_account(resource)
                        if not resource_actions[resource_name]["type"]:
                            resource_actions[resource_name][
                                "type"
                            ] = get_service_from_arn(resource)
                        if not resource_actions[resource_name]["region"]:
                            resource_actions[resource_name][
                                "region"
                            ] = get_region_from_arn(resource)
                        resource_actions[resource_name]["arns"].append(resource)
                        actions = get_actions_for_resource(resource, statement)
                        resource_actions[resource_name]["actions"].extend(
                            x
                            for x in actions
                            if x not in resource_actions[resource_name]["actions"]
                        )
    return dict(resource_actions)


def get_actions_for_resource(resource_arn: str, statement: Dict) -> List[str]:
    """For the given resource and policy statement, return the actions that are
    for that resource's service.
    """
    results: List[str] = []
    # Get service from resource
    resource_service = get_service_from_arn(resource_arn)
    # Get relevant actions from policy doc
    actions = statement.get("Action", [])
    actions = actions if isinstance(actions, list) else [actions]
    for action in actions:
        if action == "*":
            results.append(action)
        else:
            if get_service_from_action(action) == resource_service:
                if action not in results:
                    results.append(action)

    return results


async def get_formatted_policy_changes(account_id, arn, request):
    aws = get_plugin_by_name(config.get("plugins.aws", "default_aws"))()
    existing_role: dict = await aws.fetch_iam_role(account_id, arn, force_refresh=True)
    policy_changes: list = json.loads(request.get("policy_changes"))
    formatted_policy_changes = []

    # Parse request json and figure out how to present to the page
    for policy_change in policy_changes:
        if not policy_change.get("inline_policies"):
            policy_change["inline_policies"] = []

        if len(policy_change.get("inline_policies")) > 1:
            raise InvalidRequestParameter(
                "Only one inline policy change at a time is currently supported."
            )

        for inline_policy in policy_change.get("inline_policies"):
            if policy_change.get("arn") != arn:
                raise InvalidRequestParameter(
                    "Only one role can be changed in a request"
                )
            policy_name = inline_policy.get("policy_name")
            await validate_policy_name(policy_name)
            policy_document = inline_policy.get("policy_document")
            old_policy = {}
            new_policy: bool = False
            existing_policy_document = {}
            if request.get("status") == "approved":
                old_policy = request.get("old_policy", {})
                if old_policy:
                    existing_policy_document = json.loads(old_policy)[0]
            if not old_policy:
                existing_inline_policies = existing_role["policy"].get(
                    "RolePolicyList", []
                )
                existing_policy_document = {}
                for existing_policy in existing_inline_policies:
                    if existing_policy["PolicyName"] == policy_name:
                        existing_policy_document = existing_policy["PolicyDocument"]

            # Generate dictionary with old / new policy documents
            diff = DeepDiff(existing_policy_document, policy_document)

            if not existing_policy_document:
                new_policy = True

            formatted_policy_changes.append(
                {
                    "name": policy_name,
                    "old": existing_policy_document,
                    "new": policy_document,
                    "diff": diff,
                    "new_policy": new_policy,
                }
            )

        assume_role_policy_document = policy_change.get("assume_role_policy_document")
        if assume_role_policy_document:
            if policy_change.get("arn") != arn:
                raise InvalidRequestParameter(
                    "Only one role can be changed in a request"
                )
            existing_ar_policy = existing_role["policy"]["AssumeRolePolicyDocument"]
            old_policy = request.get("old_policy", {})
            if old_policy:
                existing_ar_policy = json.loads(old_policy)[0]

            diff = DeepDiff(
                existing_ar_policy,
                assume_role_policy_document.get("assume_role_policy_document"),
            )

            formatted_policy_changes.append(
                {
                    "name": "AssumeRolePolicyDocument",
                    "old": existing_ar_policy,
                    "new": assume_role_policy_document.get(
                        "assume_role_policy_document"
                    ),
                    "new_policy": False,
                    "diff": diff,
                }
            )

        resource_policy_documents = request.get("resource_policies")
        if resource_policy_documents:
            for resource in resource_policy_documents:
                existing_policy_document = None
                # TODO: make this actually fetch the resource policy
                # existing_policy_document = aws.fetch_resource_policy()
                new_policy_document = resource["policy_document"]
                diff = DeepDiff(existing_policy_document, new_policy_document)

                formatted_policy_changes.append(
                    {
                        "name": "ResourcePolicy",
                        "old": existing_policy_document,
                        "new": new_policy_document,
                        "new_policy": not existing_policy_document,
                        "diff": diff,
                    }
                )
    return {"changes": formatted_policy_changes, "role": existing_role}


async def should_auto_approve_policy(events, user, user_groups):
    aws = get_plugin_by_name(config.get("plugins.aws", "default_aws"))()
    result = await aws.should_auto_approve_policy(events, user, user_groups)
    return result


async def should_auto_approve_policy_v2(
    extended_request: ExtendedRequestModel, user, user_groups
):
    """
    This uses your fancy internal logic to determine if a request should be auto-approved or not. The default plugin
    set included in ConsoleMe OSS will return False.
    """
    aws = get_plugin_by_name(config.get("plugins.aws", "default_aws"))()
    return await aws.should_auto_approve_policy_v2(extended_request, user, user_groups)


async def send_communications_policy_change_request_v2(
    extended_request: ExtendedRequestModel,
):
    """
        Send an email for a status change for a policy request

    :param extended_request: ExtendedRequestModel
    :return:
    """
    request_uri = await get_policy_request_uri_v2(extended_request)
    await send_policy_request_status_update_v2(extended_request, request_uri)


async def send_communications_new_comment(
    extended_request: ExtendedRequestModel, user: str, to_addresses=None
):
    """
            Send an email for a new comment.
            Note: until ABAC work is completed, if to_addresses is empty, we will send an email to
                fallback reviewers

    :param extended_request: ExtendedRequestModel
    :param user: user making the comment
    :param to_addresses: List of addresses to send the email to
    :return:
    """
    if not to_addresses:
        to_addresses = config.get("groups.fallback_policy_request_reviewers", [])

    request_uri = await get_policy_request_uri_v2(extended_request)
    await send_new_comment_notification(
        extended_request, to_addresses, user, request_uri
    )


async def get_resource_type_for_arn(arn: str) -> str:
    return arn.split(":")[2]


async def get_region_for_arn(arn: str) -> str:
    # TODO: Provide region for S3 buckets and other organization resource types where it isn't known?
    return arn.split(":")[3]


async def get_resource_name_for_arn(arn: str) -> str:
    resource_name = arn.split(":")[5]
    if "/" in resource_name:
        resource_name = resource_name.split("/")[-1]
    return resource_name


async def get_url_for_resource(
    arn, resource_type=None, account_id=None, region=None, resource_name=None
):
    if not resource_type:
        resource_type = await get_resource_type_for_arn(arn)
    if not account_id:
        account_id = await get_resource_account(arn)
    if not region:
        region = await get_region_for_arn(arn)
    if not resource_name:
        resource_name = await get_resource_name_for_arn(arn)
    url = ""
    if resource_type == "iam":
        resource_name = arn.split("/")[-1]
        url = f"/policies/edit/{account_id}/iamrole/{resource_name}"
    elif resource_type == "s3":
        url = f"/policies/edit/{account_id}/s3/{resource_name}"
    elif resource_type in ["sqs", "sns"]:
        url = f"/policies/edit/{account_id}/{resource_type}/{region}/{resource_name}"
    elif resource_type == "AWS::CloudFormation::Stack":
        url = f"/role/{account_id}?redirect=https://console.aws.amazon.com/cloudformation/home?region={region}#/stacks/"
    elif resource_type == "AWS::CloudFront::Distribution":
        url = f"/role/{account_id}?redirect=https://console.aws.amazon.com/cloudfront/home?%23distribution-settings:{resource_name}"
    elif resource_type == "AWS::CloudTrail::Trail":
        url = f"/role/{account_id}?redirect=https://console.aws.amazon.com/cloudtrail/home?region={region}%23/configuration"
    elif resource_type == "AWS::CloudWatch::Alarm":
        url = (
            f"/role/{account_id}?redirect=https://console.aws.amazon.com/cloudwatch/home"
            f"?region={region}%23alarmsV2:"
        )
    elif resource_type == "AWS::CodeBuild::Project":
        url = (
            f"/role/{account_id}?redirect=https://console.aws.amazon.com/codesuite/codebuild/"
            f"{account_id}/projects/{resource_name}/history?region={region}"
        )
    elif resource_type == "AWS::CodePipeline::Pipeline":
        url = (
            f"/role/{account_id}?redirect="
            "https://console.aws.amazon.com/codesuite/codepipeline/pipelines/"
            f"{resource_name}/view?region={region}"
        )
    elif resource_type == "AWS::DynamoDB::Table":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/dynamodb/home?region={region}%23tables:selected={resource_name}"
        )
    elif resource_type == "AWS::EC2::CustomerGateway":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23CustomerGateways:search={resource_name}"
        )
    elif resource_type == "AWS::EC2::InternetGateway":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23igws:search={resource_name}"
        )
    elif resource_type == "AWS::EC2::NatGateway":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23NatGateways:search={resource_name}"
        )
    elif resource_type == "AWS::EC2::NetworkAcl":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23acls:search={resource_name}"
        )
    elif resource_type == "AWS::EC2::RouteTable":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23RouteTables:search={resource_name}"
        )
    elif resource_type == "AWS::EC2::SecurityGroup":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/ec2/v2/home?region={region}%23SecurityGroup:groupId={resource_name}"
        )
    elif resource_type == "AWS::EC2::Subnet":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23subnets:search={resource_name}"
        )
    elif resource_type == "AWS::EC2::VPC":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23vpcs:search={resource_name}"
        )
    elif resource_type == "AWS::EC2::VPCEndpoint":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23Endpoints:search={resource_name}"
        )
    elif resource_type == "AWS::EC2::VPCEndpointService":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23EndpointServices:search={resource_name}"
        )
    elif resource_type == "AWS::EC2::VPCPeeringConnection":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23PeeringConnections:search={resource_name}"
        )
    elif resource_type == "AWS::EC2::VPNConnection":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23VpnConnections:search={resource_name}"
        )
    elif resource_type == "AWS::EC2::VPNGateway":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23VpnGateways:search={resource_name}"
        )
    elif resource_type == "AWS::ElasticBeanstalk::Application":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/elasticbeanstalk/home?region={region}%23/applications"
        )
    elif resource_type == "AWS::ElasticBeanstalk::ApplicationVersion":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/elasticbeanstalk/home?region={region}%23/applications"
        )
    elif resource_type == "AWS::ElasticBeanstalk::Environment":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/elasticbeanstalk/home?region={region}%23/environments"
        )
    elif resource_type == "AWS::ElasticLoadBalancing::LoadBalancer":
        url = (
            f"/role/{account_id}?redirect="
            "https://console.aws.amazon.com"
            f"/ec2/v2/home?region={region}%23LoadBalancers:search={resource_name}"
        )
    elif resource_type == "AWS::ElasticLoadBalancingV2::LoadBalancer":
        resource_name = arn.split("/")[2]
        url = (
            f"/role/{account_id}?redirect="
            "https://console.aws.amazon.com"
            f"/ec2/v2/home?region={region}%23LoadBalancers:search={resource_name}"
        )
    elif resource_type == "AWS::Elasticsearch::Domain":
        url = (
            f"/role/{account_id}?redirect="
            "https://console.aws.amazon.com"
            f"/es/home?region={region}%23domain:resource={resource_name};action=dashboard;tab=undefined"
        )
    elif resource_type == "AWS::Lambda::Function":
        resource_name = arn.split(":")[6]
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/lambda/home?region={region}%23/functions/{resource_name}"
        )
    elif resource_type == "AWS::RDS::DBSnapshot":
        resource_name = arn.split(":")[6]
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/rds/home?region={region}%23db-snapshot:id={resource_name}"
        )
    # TBD
    elif resource_type == "AWS::Redshift::Cluster":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/rds/home?region={region}%23db-snapshot:id={resource_name}"
        )
    elif resource_type == "AWS::IAM::Policy":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/iam/home?%23/policies/{arn}$serviceLevelSummary"
        )
    elif resource_type == "AWS::IAM::User":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/iam/home?%23/users/{resource_name}"
        )
    elif resource_type == "AWS::IAM::Group":
        url = f"/role/{account_id}?redirect=https://console.aws.amazon.com/iam/home?%23/groups/{resource_name}"
    elif resource_type == "AWS::Shield::Protection":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/wafv2/shield%23/tedx"
        )
    elif resource_type == "AWS::ShieldRegional::Protection":
        url = (
            f"/role/{account_id}?redirect="
            f"https://console.aws.amazon.com/wafv2/shield%23/tedx"
        )
    elif resource_type in ["AWS::WAF::RateBasedRule", "AWS::WAF::Rule"]:
        url = (
            f"/role/{account_id}?redirect=" f"https://console.aws.amazon.com/wafv2/home"
        )
    elif resource_type == "AWS::WAF::RuleGroup":
        url = (
            f"/role/{account_id}?redirect=" f"https://console.aws.amazon.com/wafv2/fms"
        )
    elif resource_type == "AWS::WAF::WebACL":
        url = (
            f"/role/{account_id}?redirect=" f"https://console.aws.amazon.com/wafv2/home"
        )

    return url


async def get_aws_config_history_url_for_resource(
    account_id, resource_id, resource_name, technology, region="us-east-1"
):
    if config.get("get_aws_config_history_url_for_resource.generate_conglomo_url"):
        return await get_conglomo_url_for_resource(
            account_id, resource_id, technology, region
        )

    encoded_redirect = urllib.parse.quote_plus(
        f"https://{region}.console.aws.amazon.com/config/home?#/resources/timeline?"
        f"resourceId={resource_id}&resourceName={resource_name}&resourceType={technology}"
    )

    url = f"/role/{account_id}?redirect={encoded_redirect}"
    return url


async def get_conglomo_url_for_resource(
    account_id, resource_id, technology, region="global"
):
    conglomo_url = config.get("get_aws_config_history_url_for_resource.conglomo_url")
    if not conglomo_url:
        raise MissingConfigurationValue(
            "Unable to find conglomo URL in configuration: `get_aws_config_history_url_for_resource.conglomo_url`"
        )
    encoded_resource_id = base64.urlsafe_b64encode(resource_id.encode("utf-8")).decode(
        "utf-8"
    )
    return f"{conglomo_url}/resource/{account_id}/{region}/{technology}/{encoded_resource_id}"

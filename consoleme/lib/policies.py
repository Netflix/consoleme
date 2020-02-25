import base64
import re
import sys
import time
from collections import defaultdict
from typing import Dict, List

import boto3
import ujson as json
from asgiref.sync import sync_to_async
from botocore.exceptions import ClientError
from cloudaux.aws.sts import boto3_cached_conn
from deepdiff import DeepDiff
from policy_sentry.util.actions import get_service_from_action
from policy_sentry.util.arns import get_service_from_arn

from consoleme.config import config
from consoleme.exceptions.exceptions import InvalidRequestParameter
from consoleme.lib.plugins import get_plugin_by_name

log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics"))()
try:
    zelkova = boto3.client("zelkova", region_name=config.region)
except Exception as e:  # noqa
    zelkova = None
    config.sentry.captureException()


async def invalid_characters_in_policy(policy_value):
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
            requester: str = split_items[0][
                : (64 - (len(split_items[-1]) + 1))
            ] + "@" + split_items[-1]

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

            # Todo(ccastrapel): Integrate Zelkova
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


async def can_move_back_to_pending(request, groups):
    if request.get("status") in ["cancelled", "rejected"]:
        # Don't allow returning requests to pending state if more than a day has passed since the last update
        if request.get("last_updated", 0) < int(time.time()) - 86400:
            return False
        # Allow admins to return requests back to pending state
        for g in config.get("groups.can_admin_policies"):
            if g in groups:
                return True
    return False


async def can_update_requests(request, user, groups):
    # Users can update their own requests
    can_update = True if user in request["username"] else False

    # Allow admins to return requests back to pending state
    if not can_update:
        for g in config.get("groups.can_admin_policies"):
            if g in groups:
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
            result["error"] = log_data["error"]
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
    # Invoke Lambda and wait for response
    client = boto3.client("lambda", region_name=config.region)

    response = await sync_to_async(client.invoke)(
        FunctionName="roleupdater_lambda",
        LogType="Tail",
        Payload=str.encode(json.dumps(events, escape_forward_slashes=False)),
    )

    response_log = base64.b64decode(response["LogResult"])
    log_data["lambda_response"] = response_log
    log.debug(log_data)

    if response.get("FunctionError"):
        log_data["message"] = "Error"
        log_data["error"] = json.dumps(response)
        log.error(log_data)
        result["status"] = "error"
        result["error"] = log_data["error"]
        return result

    elif response.get("Payload"):
        payload = json.loads(response["Payload"].read())
        if not payload.get("success"):
            log_data["message"] = "Error"
            log_data["error"] = payload.get("message")
            log.error(log_data)
            result["status"] = "error"
            result["error"] = log_data["error"]
            return result

    return result


async def can_manage_policy_requests(groups):
    approval_groups = config.get("groups.can_admin_policies", [])

    for g in approval_groups:
        if g in groups:
            return True
    return False


async def get_policy_request_uri(request):
    return f"{config.get('url')}/policies/request/{request['request_id']}"


async def validate_policy_name(policy_name):
    p = re.compile("^[a-zA-Z0-9+=,.@\\-_]+$")
    match = p.match(policy_name)
    if not match:
        raise InvalidRequestParameter(
            "The specified value for policyName is invalid. "
            "It must contain only alphanumeric characters and/or the following: +=,.@_-"
        )


async def get_resources_from_events(policy_changes: List[Dict]) -> Dict[str, List[str]]:
    """Returns a dict of resources affected by a list of policy changes along with
    the actions that are relevant to them.

    Returned dict format:
    {
        "arn:aws:service1:::resource": ["service1:action1", "service1:action2"],
        "arn:aws:service2:::other_resource": ["service2:action1", "service2:action2"],
    }
    """
    resource_actions: Dict[str, List[str]] = defaultdict(list)
    for event in policy_changes:
        for policy_type in ["inline_policies", "managed_policies"]:
            for policy in event[policy_type]:
                policy_document = policy["policy_document"]
                for statement in policy_document.get("Statement", []):
                    for resource in statement.get("Resource", []):
                        actions = get_actions_for_resource(resource, statement)
                        resource_actions[resource].extend(actions)
    return dict(resource_actions)


def get_actions_for_resource(resource: str, statement: Dict) -> List[str]:
    """For the given resource and list of actions, return the actions that are
    for that resource's service.
    """
    results: List[str] = []
    # Get service from resource
    resource_service = get_service_from_arn(resource)
    # Get relevant actions from policy doc
    for action in statement["Action"]:
        if get_service_from_action(action) == resource_service:
            results.append(action)

    return list(set(results))


async def get_formatted_policy_changes(account_id, arn, request):
    aws = get_plugin_by_name(config.get("plugins.aws"))()
    existing_role: dict = await aws.fetch_iam_role(account_id, arn, force_refresh=True)
    policy_changes: list = json.loads(request.get("policy_changes"))
    formatted_policy_changes = []

    if len(policy_changes) > 1:  # TODO: Support multiple policy changes
        raise InvalidRequestParameter(
            "Only one policy change can be included in a policy change request"
        )
    # Parse request json and figure out how to present to the page
    for policy_change in policy_changes:
        if not policy_change.get("inline_policies"):
            policy_change["inline_policies"] = []
        if policy_change.get("arn") != arn:
            raise InvalidRequestParameter("Only one role can be changed in a request")

        if len(policy_change.get("inline_policies")) > 1:
            raise InvalidRequestParameter(
                "Only one inline policy change at a time is currently supported."
            )

        for inline_policy in policy_change.get("inline_policies"):
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
    return {"changes": formatted_policy_changes, "role": existing_role}


async def should_auto_approve_policy(events, user, user_groups):
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {"function": function, "user": user}

    try:
        if not config.get("dynamic_config.policy_request_autoapprove_probes.enabled"):
            return False
        for event in events:
            arn = event.get("arn")
            account_id = arn.split(":")[4]
            log_data = {
                "function": function,
                "requested_policy": event,
                "user": user,
                "arn": arn,
            }

            inline_policies = event.get("inline_policies", [])
            approving_probe = None
            # We only support inline policies at this time
            if not inline_policies:
                return False

            # We only want to analyze update and attach events
            for policy in inline_policies:
                policy_result = False
                if policy.get("action") not in ["update", "attach"]:
                    return False

                if not zelkova:
                    return False

                for probe in config.get(
                    "dynamic_config.policy_request_autoapprove_probes.probes"
                ):
                    log_data["probe"] = probe["name"]
                    log_data["requested_policy"] = policy
                    log_data["message"] = "Running probe on requested policy"
                    probe_result = False
                    requested_policy_text = policy["policy_document"]

                    # Do not approve "Deny" policies automatically
                    if isinstance(requested_policy_text, dict):
                        statements = requested_policy_text.get("Statement", [])
                        for statement in statements:
                            if not isinstance(statement, dict):
                                continue
                            if statement.get("Effect") == "Deny":
                                return False

                    if isinstance(requested_policy_text, dict):
                        requested_policy_text = json.dumps(requested_policy_text)
                    zelkova_result = await sync_to_async(zelkova.compare_policies)(
                        Items=[
                            {
                                "Policy0": requested_policy_text,
                                "Policy1": probe["policy"].replace(
                                    "{account_id}", account_id
                                ),
                                "ResourceType": "IAM",
                            }
                        ]
                    )

                    comparison = zelkova_result["Items"][0]["Comparison"]

                    allow_listed = False
                    allowed_group = False

                    # Probe will fail if ARN account ID is not in the probe's account allow-list. Default allow-list is
                    # *
                    for account in probe.get("accounts", {}).get("allowlist", ["*"]):
                        if account == "*" or account_id == str(account):
                            allow_listed = True
                            break

                    if not allow_listed:
                        comparison = "DENIED_BY_ALLOWLIST"

                    # Probe will fail if ARN account ID is in the probe's account blocklist
                    for account in probe.get("accounts", {}).get("blocklist", []):
                        if account_id == str(account):
                            comparison = "DENIED_BY_BLOCKLIST"

                    for group in probe.get("required_user_or_group", ["*"]):
                        for g in user_groups:
                            if group == "*" or group == g or group == user:
                                allowed_group = True
                                break

                    if not allowed_group:
                        comparison = "DENIED_BY_ALLOWEDGROUPS"

                    if comparison in ["LESS_PERMISSIVE", "EQUIVALENT"]:
                        probe_result = True
                        policy_result = True
                        approving_probe = probe["name"]
                    log_data["comparison"] = comparison
                    log_data["probe_result"] = probe_result
                    log.debug(log_data)
                if not policy_result:
                    # If one of the policies in the request fails to auto-approve, everything fails
                    log_data["result"] = False
                    log_data["message"] = "Successfully ran all probes"
                    log.debug(log_data)
                    stats.count(f"{function}.called", tags={"result": False})
                    return False

            log_data["result"] = True
            log_data["message"] = "Successfully ran all probes"
            log.debug(log_data)
            stats.count(f"{function}.called", tags={"result": True})
            return {"approved": True, "approving_probe": approving_probe}
    except Exception as e:
        config.sentry.captureException()
        log_data["error"] = e
        log_data["message"] = "Exception in function"
        log.error(log_data)
        return False

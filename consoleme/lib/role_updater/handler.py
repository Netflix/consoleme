import sys
import traceback

import ujson as json
from asgiref.sync import sync_to_async
from botocore.exceptions import ClientError
from cloudaux.aws.sts import boto3_cached_conn

from consoleme.config import config
from consoleme.lib.aws import sanitize_session_name
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.role_updater.schemas import RoleUpdaterRequest

log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()


async def update_role(event):
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "event": event,
        "message": "Working on event",
    }
    log.debug(log_data)

    if not isinstance(event, list):
        raise Exception("The passed event must be a list.")

    # Let's normalize all of the policies to JSON if they are not already
    for d in event:
        for i in d.get("inline_policies", []):
            if i.get("policy_document") and isinstance(i.get("policy_document"), dict):
                i["policy_document"] = json.dumps(
                    i["policy_document"], escape_forward_slashes=False
                )

        if d.get("assume_role_policy_document", {}):
            if isinstance(
                d.get("assume_role_policy_document", {}).get(
                    "assume_role_policy_document"
                ),
                dict,
            ):
                d["assume_role_policy_document"][
                    "assume_role_policy_document"
                ] = json.dumps(
                    d["assume_role_policy_document"]["assume_role_policy_document"],
                    escape_forward_slashes=False,
                )

    bad_validation = RoleUpdaterRequest().validate(event, many=True)
    if bad_validation:
        log_data["error"] = bad_validation
        log.error(log_data)
        return {"error_msg": "invalid schema passed", "detail_error": bad_validation}

    event = RoleUpdaterRequest().load(event, many=True)

    result = {"success": False}

    for d in event:
        arn = d["arn"]
        aws_session_name = sanitize_session_name("roleupdater-" + d["requester"])
        account_number = await parse_account_id_from_arn(arn)
        role_name = await parse_role_name_from_arn(arn)
        # TODO: Make configurable
        client = boto3_cached_conn(
            "iam",
            account_number=account_number,
            assume_role=config.get("policies.role_name", "ConsoleMe"),
            session_name=aws_session_name,
            retry_max_attempts=2,
            client_kwargs=config.get("boto3.client_kwargs", {}),
        )
        inline_policies = d.get("inline_policies", [])
        managed_policies = d.get("managed_policies", [])
        assume_role_doc = d.get("assume_role_policy_document", {})
        tags = d.get("tags", [])

        if (
            not inline_policies
            and not managed_policies
            and not assume_role_doc
            and not tags
        ):
            result["message"] = f"Invalid request. No response taken on event: {event}"
            return result

        try:
            for policy in inline_policies:
                await update_inline_policy(client, role_name, policy)

            for policy in managed_policies:
                await update_managed_policy(client, role_name, policy)

            if assume_role_doc:
                await update_assume_role_document(client, role_name, assume_role_doc)

            for tag in tags:
                await update_tags(client, role_name, tag)
        except ClientError as ce:
            result["message"] = ce.response["Error"]
            result["Traceback"] = traceback.format_exc()
            return result
        result["success"] = True
        return result


async def parse_account_id_from_arn(arn):
    return arn.split(":")[4]


async def parse_role_name_from_arn(arn):
    return arn.split("/")[-1]


async def update_inline_policy(client, role_name, policy):
    log.debug(
        {"message": "Updating inline policy", "role_name": role_name, "policy": policy}
    )
    if policy.get("action") == "attach":
        response = await sync_to_async(client.put_role_policy)(
            RoleName=role_name,
            PolicyName=policy["policy_name"],
            PolicyDocument=policy["policy_document"],
        )
    elif policy.get("action") == "detach":
        response = await sync_to_async(client.delete_role_policy)(
            RoleName=role_name, PolicyName=policy["policy_name"]
        )
    else:
        raise Exception("Unable to update managed policy")
    return response


async def update_managed_policy(client, role_name, policy):
    log.debug(
        {"message": "Updating managed policy", "role_name": role_name, "policy": policy}
    )
    if policy.get("action") == "attach":
        response = await sync_to_async(client.attach_role_policy)(
            PolicyArn=policy["arn"], RoleName=role_name
        )
    elif policy.get("action") == "detach":
        response = await sync_to_async(client.detach_role_policy)(
            PolicyArn=policy["arn"], RoleName=role_name
        )
    else:
        raise Exception("Unable to update managed policy.")
    return response


async def update_assume_role_document(client, role_name, assume_role_doc):
    log.debug(
        {
            "message": "Updating assume role doc",
            "role_name": role_name,
            "assume_role_doc": assume_role_doc,
        }
    )
    response = None
    if assume_role_doc.get("action", "") in ["create", "update"]:
        response = await sync_to_async(client.update_assume_role_policy)(
            RoleName=role_name,
            PolicyDocument=assume_role_doc["assume_role_policy_document"],
        )
    return response
    # Log or report result?


async def update_tags(client, role_name, tag):
    log.debug({"message": "Updating tag", "role_name": role_name, "tag": tag})
    if tag.get("action") == "add":
        response = await sync_to_async(client.tag_role)(
            RoleName=role_name, Tags=[{"Key": tag["key"], "Value": tag["value"]}]
        )
    elif tag.get("action") == "remove":
        response = await sync_to_async(client.untag_role)(
            RoleName=role_name, TagKeys=[tag["key"]]
        )
    else:
        raise Exception("Unable to update tags.")
    return response

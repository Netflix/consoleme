import asyncio
import re
import sys
import time
import uuid
from hashlib import sha256
from typing import Dict, List, Optional, Union

import sentry_sdk
import ujson as json
from asgiref.sync import sync_to_async
from botocore.exceptions import ClientError
from cloudaux.aws.iam import get_managed_policy_document
from cloudaux.aws.sts import boto3_cached_conn
from policy_sentry.util.actions import get_service_from_action
from policy_sentry.util.arns import parse_arn

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    InvalidRequestParameter,
    NoMatchingRequest,
    ResourceNotFound,
    Unauthorized,
    UnsupportedChangeType,
)
from consoleme.lib.account_indexers import get_account_id_to_name_mapping
from consoleme.lib.auth import can_admin_policies
from consoleme.lib.aws import (
    create_or_update_managed_policy,
    fetch_resource_details,
    generate_updated_resource_policy,
    get_bucket_location_with_fallback,
    get_region_from_arn,
    get_resource_account,
    get_resource_from_arn,
    get_resource_policy,
    get_service_from_arn,
    sanitize_session_name,
)
from consoleme.lib.change_request import generate_policy_name
from consoleme.lib.dynamo import UserDynamoHandler
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.policies import (
    can_move_back_to_pending_v2,
    can_update_cancel_requests_v2,
    get_url_for_resource,
    invalid_characters_in_policy,
    send_communications_new_comment,
    send_communications_policy_change_request_v2,
)
from consoleme.lib.templated_resources.requests import (
    generate_honeybee_request_from_change_model_array,
)
from consoleme.lib.v2.aws_principals import get_role_details, get_user_details
from consoleme.models import (
    Action,
    ActionResult,
    ApplyChangeModificationModel,
    AssumeRolePolicyChangeModel,
    CancelChangeModificationModel,
    ChangeModel,
    ChangeModelArray,
    Command,
    CommentModel,
    CommentRequestModificationModel,
    ExtendedAwsPrincipalModel,
    ExtendedRequestModel,
    GenericFileChangeModel,
    InlinePolicyChangeModel,
    ManagedPolicyChangeModel,
    ManagedPolicyResourceChangeModel,
    PermissionsBoundaryChangeModel,
    PolicyModel,
    PolicyRequestModificationRequestModel,
    PolicyRequestModificationResponseModel,
    RequestCreationModel,
    RequestCreationResponse,
    RequestStatus,
    ResourceModel,
    ResourcePolicyChangeModel,
    ResourceTagChangeModel,
    Status,
    TagAction,
    UpdateChangeModificationModel,
    UserModel,
)

log = config.get_logger()
auth = get_plugin_by_name(config.get("plugins.auth", "default_auth"))()
aws = get_plugin_by_name(config.get("plugins.aws", "default_aws"))()


async def generate_request_from_change_model_array(
    request_creation: RequestCreationModel, user: str
) -> ExtendedRequestModel:
    """
    Compiles an ChangeModelArray and returns a filled out ExtendedRequestModel based on the changes

    :param request_creation: ChangeModelArray
    :param user: Str - requester's email address
    :return: ChangeModelArray
    """

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "request": request_creation.dict(),
        "message": "Incoming request",
    }
    log.info(log_data)

    primary_principal = None
    change_models = request_creation.changes
    if len(change_models.changes) < 1:
        log_data["message"] = "At least 1 change is required to create a request."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    inline_policy_changes = []
    managed_policy_changes = []
    resource_policy_changes = []
    assume_role_policy_changes = []
    resource_tag_changes = []
    permissions_boundary_changes = []
    managed_policy_resource_changes = []
    generic_file_changes = []
    role = None

    extended_request_uuid = str(uuid.uuid4())
    incremental_change_id = 0
    supported_resource_policies = config.get(
        "policies.supported_resource_types_for_policy_application", ["s3", "sqs", "sns"]
    )

    for change in change_models.changes:
        # All changes status must be not-applied at request creation
        change.status = Status.not_applied
        # Add ID for each change
        change.id = extended_request_uuid + str(incremental_change_id)
        incremental_change_id += 1

        # Enforce a maximum of one principal ARN per ChangeGeneratorModelArray (aka Policy Request)
        if not primary_principal:
            primary_principal = change.principal
        if primary_principal != change.principal:
            log_data[
                "message"
            ] = "We only support making changes to a single principal ARN per request."
            log.error(log_data)
            raise InvalidRequestParameter(log_data["message"])

        if change.change_type == "inline_policy":
            inline_policy_changes.append(
                InlinePolicyChangeModel.parse_obj(change.__dict__)
            )
        elif change.change_type == "managed_policy":
            managed_policy_changes.append(
                ManagedPolicyChangeModel.parse_obj(change.__dict__)
            )
        elif change.change_type == "managed_policy_resource":
            managed_policy_resource_changes.append(
                ManagedPolicyResourceChangeModel.parse_obj(change.__dict__)
            )
        elif change.change_type == "resource_policy":
            change.autogenerated = False
            change.source_change_id = None
            resource_arn_parsed = parse_arn(change.arn)
            resource_type = resource_arn_parsed["service"]
            if resource_type in supported_resource_policies:
                change.supported = True
            else:
                change.supported = False
            resource_policy_changes.append(change)
        elif change.change_type == "assume_role_policy":
            assume_role_policy_changes.append(
                AssumeRolePolicyChangeModel.parse_obj(change.__dict__)
            )
        elif change.change_type == "resource_tag":
            resource_tag_changes.append(
                ResourceTagChangeModel.parse_obj(change.__dict__)
            )
        elif change.change_type == "permissions_boundary":
            permissions_boundary_changes.append(
                PermissionsBoundaryChangeModel.parse_obj(change.__dict__)
            )
        elif change.change_type == "generic_file":
            generic_file_changes.append(
                GenericFileChangeModel.parse_obj(change.__dict__)
            )
        else:
            raise UnsupportedChangeType(
                f"Invalid `change_type` for change: {change.__dict__}"
            )

    # Make sure the requester is only ever 64 chars with domain
    if len(user) > 64:
        split_items: list = user.split("@")
        user: str = (
            split_items[0][: (64 - (len(split_items[-1]) + 1))] + "@" + split_items[-1]
        )

    if primary_principal.principal_type == "AwsResource":
        # TODO: Separate this out into another function
        account_id = await get_resource_account(primary_principal.principal_arn)
        arn_parsed = parse_arn(primary_principal.principal_arn)
        arn_type = arn_parsed["service"]
        arn_name = (
            arn_parsed["resource_path"]
            if arn_parsed["resource_path"]
            else arn_parsed["resource"]
        )
        arn_region = arn_parsed["region"]
        try:
            arn_url = await get_url_for_resource(
                arn=primary_principal.principal_arn,
                resource_type=arn_type,
                account_id=account_id,
                region=arn_region,
                resource_name=arn_name,
            )
        except ResourceNotFound:
            # should never reach this case...
            arn_url = ""

        # Only one assume role policy change allowed per request
        if len(assume_role_policy_changes) > 1:
            log_data[
                "message"
            ] = "One one assume role policy change supported per request."
            log.error(log_data)
            raise InvalidRequestParameter(log_data["message"])

        if len(managed_policy_resource_changes) > 0:
            # for managed policy changes, principal arn must be a managed policy
            if arn_parsed["service"] != "iam" or arn_parsed["resource"] != "policy":
                log_data[
                    "message"
                ] = "Principal ARN type not supported for managed policy resource changes."
                log.error(log_data)
                raise InvalidRequestParameter(log_data["message"])

            if arn_parsed["account"] == "aws":
                log_data["message"] = "AWS Managed Policies aren't valid for changes."
                log.error(log_data)
                raise InvalidRequestParameter(log_data["message"])

            if (
                len(inline_policy_changes) > 0
                or len(managed_policy_changes) > 0
                or len(assume_role_policy_changes) > 0
                or len(permissions_boundary_changes) > 0
            ):
                log_data[
                    "message"
                ] = "Principal ARN type not supported for inline/managed/assume role policy changes."
                log.error(log_data)
                raise InvalidRequestParameter(log_data["message"])

            if len(managed_policy_resource_changes) > 1:
                log_data[
                    "message"
                ] = "One one managed policy resource change supported per request."
                log.error(log_data)
                raise InvalidRequestParameter(log_data["message"])

            policy_name = arn_parsed["resource_path"].split("/")[-1]
            managed_policy_resource = None
            try:
                managed_policy_resource = await sync_to_async(
                    get_managed_policy_document
                )(
                    policy_arn=primary_principal.principal_arn,
                    account_number=account_id,
                    assume_role=config.get("policies.role_name"),
                    region=config.region,
                    retry_max_attempts=2,
                )
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchEntity":
                    # Could be a new managed policy, hence not found
                    pass
                else:
                    log_data[
                        "message"
                    ] = "Exception raised while getting managed policy"
                    log.error(log_data, exc_info=True)
                    raise InvalidRequestParameter(log_data["message"] + ": " + str(e))

            for managed_policy_resource_change in managed_policy_resource_changes:
                await validate_managed_policy_resource_change(
                    managed_policy_resource_change,
                    policy_name,
                    user,
                    managed_policy_resource,
                )

        elif (
            len(inline_policy_changes) > 0
            or len(managed_policy_changes) > 0
            or len(assume_role_policy_changes) > 0
            or len(permissions_boundary_changes) > 0
        ):
            # for inline/managed/assume role policies, principal arn must be a role
            if arn_parsed["service"] != "iam" or arn_parsed["resource"] not in [
                "role",
                "user",
            ]:
                log_data[
                    "message"
                ] = "Resource not found, or ARN type not supported for inline/managed/assume role policy changes."
                log.error(log_data)
                raise InvalidRequestParameter(log_data["message"])
            principal_name = arn_parsed["resource_path"].split("/")[-1]
            principal_details = None
            if arn_parsed["resource"] == "role":
                principal_details = await get_role_details(
                    account_id, role_name=principal_name, extended=True
                )
            elif arn_parsed["resource"] == "user":
                principal_details = await get_user_details(
                    account_id, user_name=principal_name, extended=True
                )
            if not principal_details:
                log_data["message"] = "Principal not found"
                log.error(log_data)
                raise InvalidRequestParameter(log_data["message"])
            for inline_policy_change in inline_policy_changes:
                inline_policy_change.policy_name = await generate_policy_name(
                    inline_policy_change.policy_name,
                    user,
                    inline_policy_change.expiration_date,
                )
                await validate_inline_policy_change(
                    inline_policy_change, user, principal_details
                )
            for managed_policy_change in managed_policy_changes:
                await validate_managed_policy_change(
                    managed_policy_change, user, principal_details
                )
            for permissions_boundary_change in permissions_boundary_changes:
                await validate_permissions_boundary_change(
                    permissions_boundary_change, user, principal_details
                )
            for assume_role_policy_change in assume_role_policy_changes:
                if arn_parsed["resource"] == "user":
                    raise UnsupportedChangeType(
                        "Unable to modify an assume role policy associated with an IAM user"
                    )
                await validate_assume_role_policy_change(
                    assume_role_policy_change, user, principal_details
                )
            for resource_tag_change in resource_tag_changes:
                await validate_resource_tag_change(
                    resource_tag_change, user, principal_details
                )

        # TODO: validate resource policy logic when we are ready to apply that

        # If here, request is valid and can successfully be generated
        request_changes = ChangeModelArray(
            changes=inline_policy_changes
            + managed_policy_changes
            + resource_policy_changes
            + assume_role_policy_changes
            + resource_tag_changes
            + permissions_boundary_changes
            + managed_policy_resource_changes
        )
        extended_request = ExtendedRequestModel(
            admin_auto_approve=request_creation.admin_auto_approve,
            id=extended_request_uuid,
            principal=primary_principal,
            timestamp=int(time.time()),
            justification=request_creation.justification,
            requester_email=user,
            approvers=[],  # TODO: approvers logic (future feature)
            request_status=RequestStatus.pending,
            changes=request_changes,
            requester_info=UserModel(
                email=user,
                extended_info=await auth.get_user_info(user),
                details_url=config.config_plugin().get_employee_info_url(user),
                photo_url=config.config_plugin().get_employee_photo_url(user),
            ),
            comments=[],
            cross_account=False,
            arn_url=arn_url,
        )
        extended_request = await populate_old_policies(extended_request, user, role)
        extended_request = await generate_resource_policies(extended_request, user)
        if len(managed_policy_resource_changes) > 0:
            await populate_old_managed_policies(extended_request, user)

    elif primary_principal.principal_type == "HoneybeeAwsResourceTemplate":
        # TODO: Generate extended request from HB template
        extended_request = await generate_honeybee_request_from_change_model_array(
            request_creation, user, extended_request_uuid
        )
    else:
        raise Exception("Unknown principal type")

    return extended_request


async def get_request_url(extended_request: ExtendedRequestModel) -> str:
    if extended_request.principal.principal_type == "AwsResource":
        return f"/policies/request/{extended_request.id}"
    elif extended_request.principal.principal_type == "HoneybeeAwsResourceTemplate":
        return extended_request.request_url
    else:
        raise Exception("Unsupported principal type")


async def is_request_eligible_for_auto_approval(
    extended_request: ExtendedRequestModel, user: str
) -> bool:
    """
    Checks whether a request is eligible for auto-approval probes or not. Currently, only requests with inline_policies
    are eligible for auto-approval probes.

    :param extended_request: ExtendedRequestModel
    :param user: username
    :return bool:
    """
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "arn": extended_request.principal.principal_arn,
        "request": extended_request.dict(),
        "message": "Checking whether request is eligible for auto-approval probes",
    }
    log.info(log_data)
    is_eligible = False

    # Currently the only allowances are: Inline policies
    for change in extended_request.changes.changes:
        # Exclude auto-generated resource policies from eligibility check
        if (
            change.change_type == "resource_policy"
            or change.change_type == "sts_resource_policy"
        ) and change.autogenerated:
            continue
        if change.change_type != "inline_policy":
            log_data[
                "message"
            ] = "Finished checking whether request is eligible for auto-approval probes"
            log_data["eligible_for_auto_approval"] = is_eligible
            log.info(log_data)
            return is_eligible

    # If above check passes, then it's eligible for auto-approval probe check
    is_eligible = True
    log_data[
        "message"
    ] = "Finished checking whether request is eligible for auto-approval probes"
    log_data["eligible_for_auto_approval"] = is_eligible
    log.info(log_data)
    return is_eligible


async def generate_resource_policies(extended_request: ExtendedRequestModel, user: str):
    """
    Generates the resource policies and adds it to the extended request.
    Note: generating resource policy is only supported for when the principal ARN is a role right now.

    :param extended_request: ExtendedRequestModel
    :param user: username
    :return:
    """
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "principal": extended_request.principal,
        "request": extended_request.dict(),
        "message": "Generating resource policies",
    }
    log.debug(log_data)

    supported_resource_policies = config.get(
        "policies.supported_resource_types_for_policy_application", ["s3", "sqs", "sns"]
    )
    supported_trust_policy_permissions = config.get(
        "policies.supported_trust_policy_permissions",
        [
            "sts:AssumeRole",
            "sts:TagSession",
            "sts:AssumeRoleWithSAML",
            "sts:AssumeRoleWithWebIdentity",
        ],
    )

    if extended_request.principal.principal_type == "AwsResource":
        principal_arn = extended_request.principal.principal_arn
        role_account_id = await get_resource_account(principal_arn)
        arn_parsed = parse_arn(principal_arn)

        if arn_parsed["service"] != "iam" or arn_parsed["resource"] != "role":
            log_data[
                "message"
            ] = "ARN type not supported for generating resource policy changes."
            log.debug(log_data)
            return extended_request

        resource_policy = {"Version": "2012-10-17", "Statement": []}
        resource_policy_sha = sha256(
            json.dumps(resource_policy, escape_forward_slashes=False).encode()
        ).hexdigest()
        if not arn_parsed.get("resource_path") or not arn_parsed.get("service"):
            return extended_request

        primary_principal_resource_model = ResourceModel(
            arn=principal_arn,
            name=arn_parsed["resource_path"].split("/")[-1],
            account_id=role_account_id,
            resource_type=arn_parsed["service"],
        )

        auto_generated_resource_policy_changes = []
        # Create resource policy stubs for current resources that are used
        for policy_change in extended_request.changes.changes:
            if policy_change.change_type == "inline_policy":
                policy_change.resources = await get_resources_from_policy_change(
                    policy_change
                )
                for resource in policy_change.resources:
                    resource_account_id = await get_resource_account(resource.arn)
                    if (
                        resource_account_id != role_account_id
                        and resource.resource_type != "iam"
                        and resource.resource_type in supported_resource_policies
                    ):
                        # Cross account
                        auto_generated_resource_policy_changes.append(
                            ResourcePolicyChangeModel(
                                arn=resource.arn,
                                policy=PolicyModel(
                                    policy_document=resource_policy,
                                    policy_sha256=resource_policy_sha,
                                ),
                                change_type="resource_policy",
                                principal=extended_request.principal,
                                status=Status.not_applied,
                                source_change_id=policy_change.id,
                                id=str(uuid.uuid4()),
                                resources=[primary_principal_resource_model],
                                autogenerated=True,
                            )
                        )
                    elif (
                        resource_account_id != role_account_id
                        and resource.resource_type == "iam"
                    ):
                        resource_added = False
                        for statement in policy_change.policy.policy_document.get(
                            "Statement", []
                        ):
                            if resource.arn in statement.get("Resource"):
                                # check if action includes supported trust policy permissions
                                statement_actions = statement.get("Action", [])
                                statement_actions = (
                                    statement_actions
                                    if isinstance(statement_actions, list)
                                    else [statement_actions]
                                )
                                for action in statement_actions:
                                    if action in supported_trust_policy_permissions:
                                        # Cross account sts policy
                                        auto_generated_resource_policy_changes.append(
                                            ResourcePolicyChangeModel(
                                                arn=resource.arn,
                                                policy=PolicyModel(
                                                    policy_document=resource_policy,
                                                    policy_sha256=resource_policy_sha,
                                                ),
                                                change_type="sts_resource_policy",
                                                principal=extended_request.principal,
                                                status=Status.not_applied,
                                                source_change_id=policy_change.id,
                                                id=str(uuid.uuid4()),
                                                resources=[
                                                    primary_principal_resource_model
                                                ],
                                                autogenerated=True,
                                            )
                                        )
                                        resource_added = True
                                        break
                            if resource_added:
                                break

        extended_request.changes.changes.extend(auto_generated_resource_policy_changes)
        if len(auto_generated_resource_policy_changes) > 0:
            extended_request.cross_account = True
        log_data["message"] = "Finished generating resource policies"
        log_data["request"] = extended_request.dict()
        log.debug(log_data)
        return extended_request


async def validate_inline_policy_change(
    change: InlinePolicyChangeModel, user: str, role: ExtendedAwsPrincipalModel
):
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "principal": change.principal.dict(),
        "policy_name": change.policy_name,
        "request": change.dict(),
        "message": "Validating inline policy change",
    }
    log.debug(log_data)
    if (
        await invalid_characters_in_policy(change.policy.policy_document)
        or await invalid_characters_in_policy(change.policy_name)
        or await invalid_characters_in_policy(change.policy.version)
    ):
        log_data["message"] = "Invalid characters were detected in the policy."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    # Can't detach a new policy
    if change.new and change.action == Action.detach:
        log_data["message"] = "Can't detach an inline policy that is new."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    seen_policy_name = False

    for existing_policy in role.inline_policies:
        # Check if a new policy is being created, ensure that we don't overwrite another policy with same name
        if change.new and change.policy_name == existing_policy.get("PolicyName"):
            log_data[
                "message"
            ] = f"Inline Policy with the name {change.policy_name} already exists."
            log.error(log_data)
            raise InvalidRequestParameter(log_data["message"])
        # Check if policy being updated is the same as existing policy.
        if (
            not change.new
            and change.policy.policy_document == existing_policy.get("PolicyDocument")
            and change.policy_name == existing_policy.get("PolicyName")
            and change.action == Action.attach
        ):
            log_data[
                "message"
            ] = f"No changes were found between the updated and existing policy for policy {change.policy_name}."
            log.error(log_data)
            raise InvalidRequestParameter(log_data["message"])
        if change.policy_name == existing_policy.get("PolicyName"):
            seen_policy_name = True

    # Trying to detach inline policy with name that isn't attached
    if change.action == Action.detach and not seen_policy_name:
        log_data[
            "message"
        ] = f"An inline policy named '{seen_policy_name}' is not attached, so we cannot remove it"
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    if change.action == Action.attach and not seen_policy_name and not change.new:
        log_data[
            "message"
        ] = f"Inline policy {change.policy_name} not seen but request claims change is not new"
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    # TODO: check sha in the request (future feature)
    # If here, then that means inline policy is validated


async def validate_permissions_boundary_change(
    change: PermissionsBoundaryChangeModel, user: str, role: ExtendedAwsPrincipalModel
):
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "principal": change.principal.dict(),
        "request": change.dict(),
        "message": "Validating permissions boundary change",
    }
    log.info(log_data)
    policy_name = change.arn.split("/")[-1]
    if await invalid_characters_in_policy(policy_name):
        log_data["message"] = "Invalid characters were detected in the policy name."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])
    if change.action == Action.attach:
        if not role.permissions_boundary:
            return
        log_data["message"] = (
            "A permissions boundary is already attached to this role. "
            "Only one permission boundary can be attached to a role."
        )
        log.error(log_data)
        raise InvalidRequestParameter(
            "A permissions boundary is already attached to this role. "
            "Only one permission boundary can be attached to a role."
        )
    elif change.action == Action.detach:
        # check to make sure permissions boundary is actually attached to the role
        if change.arn == role.permissions_boundary.get("PermissionsBoundaryArn"):
            return
        log_data[
            "message"
        ] = "The Permissions Boundary you are trying to detach is not attached to this role."
        log.error(log_data)
        raise InvalidRequestParameter(
            f"{change.arn} is not attached to this role as a permissions boundary"
        )


async def validate_managed_policy_change(
    change: ManagedPolicyChangeModel, user: str, role: ExtendedAwsPrincipalModel
):
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "principal": change.principal.dict(),
        "request": change.dict(),
        "message": "Validating managed policy change",
    }
    log.info(log_data)
    policy_name = change.arn.split("/")[-1]
    if await invalid_characters_in_policy(policy_name):
        log_data["message"] = "Invalid characters were detected in the policy name."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])
    if change.action == Action.attach:
        # check to make sure managed policy is not already attached
        for existing_policy in role.managed_policies:
            if change.arn == existing_policy.get("PolicyArn"):
                log_data[
                    "message"
                ] = "Managed Policy with that ARN already attached to this role."
                log.error(log_data)
                raise InvalidRequestParameter(
                    f"{change.arn} already attached to this role"
                )
    elif change.action == Action.detach:
        # check to make sure managed policy is actually attached to role
        seen = False
        for existing_policy in role.managed_policies:
            if change.arn == existing_policy.get("PolicyArn"):
                seen = True
                break
        if not seen:
            log_data[
                "message"
            ] = "The Managed Policy you are trying to detach is not attached to this role."
            log.error(log_data)
            raise InvalidRequestParameter(f"{change.arn} is not attached to this role")

    # TODO: check policy name is same what ARN claims


async def validate_managed_policy_resource_change(
    change: ManagedPolicyResourceChangeModel,
    policy_name: str,
    user: str,
    managed_policy_resource: Dict,
):
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "principal": change.principal.dict(),
        "request": change.dict(),
        "message": "Validating managed policy resource change",
    }
    log.info(log_data)
    if await invalid_characters_in_policy(
        policy_name
    ) or await invalid_characters_in_policy(change.policy.policy_document):
        log_data[
            "message"
        ] = "Invalid characters were detected in the policy name or document."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    if change.new and managed_policy_resource:
        # change is claiming to be a new policy, but it already exists in AWS
        log_data["message"] = "Managed policy with that ARN already exists"
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])
    elif not change.new and not managed_policy_resource:
        # change is claiming to update policy, but it doesn't exist in AWS
        log_data["message"] = "Managed policy with that ARN doesn't exist"
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    if not change.new:
        if change.policy.policy_document == managed_policy_resource:
            log_data[
                "message"
            ] = "No changes detected between current and proposed policy"
            log.error(log_data)
            raise InvalidRequestParameter(log_data["message"])


async def validate_resource_tag_change(
    change: ResourceTagChangeModel, user: str, role: ExtendedAwsPrincipalModel
):
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "principal": change.principal.dict(),
        "request": change.dict(),
        "role": role,
        "message": "Validating resource tag change",
    }
    log.debug(log_data)
    # TODO: Add validation here
    return


async def validate_assume_role_policy_change(
    change: AssumeRolePolicyChangeModel, user: str, role: ExtendedAwsPrincipalModel
):
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "principal": change.principal.dict(),
        "request": change.dict(),
        "message": "Validating assume role policy change",
    }
    log.debug(log_data)
    if await invalid_characters_in_policy(
        change.policy.policy_document
    ) or await invalid_characters_in_policy(change.policy.version):
        log_data["message"] = "Invalid characters were detected in the policy."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    # Check if policy being updated is the same as existing policy.
    if change.policy.policy_document == role.assume_role_policy_document:
        log_data[
            "message"
        ] = "No changes were found between the updated and existing assume role policy."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])


async def apply_changes_to_role(
    extended_request: ExtendedRequestModel,
    response: Union[RequestCreationResponse, PolicyRequestModificationResponseModel],
    user: str,
    specific_change_id: str = None,
) -> None:
    """
    Applies changes based on the changes array in the request, in a best effort manner to a role

    Caution: this method applies changes blindly... meaning it assumes before calling this method,
    you have validated the changes being made are authorized.

    :param extended_request: ExtendedRequestModel
    :param user: Str - requester's email address
    :param response: RequestCreationResponse
    :param specific_change_id: if this function is being used to apply only one specific change
            if not provided, all non-autogenerated, supported changes are applied
    """
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "request": extended_request.dict(),
        "message": "Applying request changes",
        "specific_change_id": specific_change_id,
    }
    log.info(log_data)

    arn_parsed = parse_arn(extended_request.principal.principal_arn)

    # Principal ARN must be a role for this function
    if arn_parsed["service"] != "iam" or arn_parsed["resource"] not in ["role", "user"]:
        log_data[
            "message"
        ] = "Resource not found, or ARN type not supported for inline/managed/assume role policy changes."
        log.error(log_data)
        response.errors += 1
        response.action_results.append(
            ActionResult(status="error", message=log_data["message"])
        )
        return

    principal_name = arn_parsed["resource_path"].split("/")[-1]
    account_id = await get_resource_account(extended_request.principal.principal_arn)
    iam_client = await sync_to_async(boto3_cached_conn)(
        "iam",
        service_type="client",
        account_number=account_id,
        region=config.region,
        assume_role=config.get("policies.role_name"),
        session_name=sanitize_session_name("principal-updater-" + user),
        retry_max_attempts=2,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=config.get(
                "aws.sts_endpoint_url", "https://sts.{region}.amazonaws.com"
            ).format(region=config.region),
        ),
        client_kwargs=config.get("boto3.client_kwargs", {}),
    )
    for change in extended_request.changes.changes:
        if change.status == Status.applied:
            # This change has already been applied, this can happen in the future when we have a multi-change request
            # that an admin approves, and it applies 5 of the changes, but fails to apply 1 change due to an error.
            # Upon correcting the error, the admin can click approve again, and it will only apply the changes that
            # haven't already been applied
            log_data[
                "message"
            ] = "Change has already been applied, skipping applying the change"
            log_data["change"] = change.dict()
            log.debug(log_data)
            continue
        if specific_change_id and change.id != specific_change_id:
            continue
        if change.change_type == "inline_policy":
            if change.action == Action.attach:
                try:
                    if arn_parsed["resource"] == "role":
                        await sync_to_async(iam_client.put_role_policy)(
                            RoleName=principal_name,
                            PolicyName=change.policy_name,
                            PolicyDocument=json.dumps(
                                change.policy.policy_document,
                                escape_forward_slashes=False,
                            ),
                        )
                    elif arn_parsed["resource"] == "user":
                        await sync_to_async(iam_client.put_user_policy)(
                            UserName=principal_name,
                            PolicyName=change.policy_name,
                            PolicyDocument=json.dumps(
                                change.policy.policy_document,
                                escape_forward_slashes=False,
                            ),
                        )
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=(
                                f"Successfully applied inline policy {change.policy_name} to principal: "
                                f"{principal_name}"
                            ),
                        )
                    )
                    change.status = Status.applied
                except Exception as e:
                    log_data["message"] = "Exception occurred applying inline policy"
                    log_data["error"] = str(e)
                    log.error(log_data, exc_info=True)
                    sentry_sdk.capture_exception()
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=(
                                f"Error occurred applying inline policy {change.policy_name} to principal: "
                                f"{principal_name}: " + str(e)
                            ),
                        )
                    )
            elif change.action == Action.detach:
                try:
                    if arn_parsed["resource"] == "role":
                        await sync_to_async(iam_client.delete_role_policy)(
                            RoleName=principal_name, PolicyName=change.policy_name
                        )
                    elif arn_parsed["resource"] == "user":
                        await sync_to_async(iam_client.delete_user_policy)(
                            UserName=principal_name, PolicyName=change.policy_name
                        )
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=(
                                f"Successfully deleted inline policy {change.policy_name} from principal: "
                                f"{principal_name}"
                            ),
                        )
                    )
                    change.status = Status.applied
                except Exception as e:
                    log_data["message"] = "Exception occurred deleting inline policy"
                    log_data["error"] = str(e)
                    log.error(log_data, exc_info=True)
                    sentry_sdk.capture_exception()
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=(
                                f"Error occurred deleting inline policy {change.policy_name} from principal: "
                                f"{principal_name} " + str(e)
                            ),
                        )
                    )
        elif change.change_type == "permissions_boundary":
            if change.action == Action.attach:
                try:
                    if arn_parsed["resource"] == "role":
                        await sync_to_async(iam_client.put_role_permissions_boundary)(
                            RoleName=principal_name, PermissionsBoundary=change.arn
                        )
                    elif arn_parsed["resource"] == "user":
                        await sync_to_async(iam_client.put_user_permissions_boundary)(
                            UserName=principal_name, PermissionsBoundary=change.arn
                        )
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=(
                                f"Successfully attached permissions boundary {change.arn} to principal: "
                                f"{principal_name}"
                            ),
                        )
                    )
                    change.status = Status.applied
                except Exception as e:
                    log_data[
                        "message"
                    ] = "Exception occurred attaching permissions boundary"
                    log_data["error"] = str(e)
                    log.error(log_data, exc_info=True)
                    sentry_sdk.capture_exception()
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=(
                                f"Error occurred attaching permissions boundary {change.arn} to principal: "
                                f"{principal_name}: " + str(e)
                            ),
                        )
                    )
            elif change.action == Action.detach:
                try:
                    if arn_parsed["resource"] == "role":
                        await sync_to_async(
                            iam_client.delete_role_permissions_boundary
                        )(RoleName=principal_name)
                    elif arn_parsed["resource"] == "user":
                        await sync_to_async(
                            iam_client.delete_user_permissions_boundary
                        )(UserName=principal_name)
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=(
                                f"Successfully detached permissions boundary {change.arn} from principal: "
                                f"{principal_name}"
                            ),
                        )
                    )
                    change.status = Status.applied
                except Exception as e:
                    log_data[
                        "message"
                    ] = "Exception occurred detaching permissions boundary"
                    log_data["error"] = str(e)
                    log.error(log_data, exc_info=True)
                    sentry_sdk.capture_exception()
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=(
                                f"Error occurred detaching permissions boundary {change.arn} "
                                f"from principal: {principal_name}: " + str(e)
                            ),
                        )
                    )
        elif change.change_type == "managed_policy":
            if change.action == Action.attach:
                try:
                    if arn_parsed["resource"] == "role":
                        await sync_to_async(iam_client.attach_role_policy)(
                            RoleName=principal_name, PolicyArn=change.arn
                        )
                    elif arn_parsed["resource"] == "user":
                        await sync_to_async(iam_client.attach_user_policy)(
                            UserName=principal_name, PolicyArn=change.arn
                        )
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=(
                                f"Successfully attached managed policy {change.arn} to principal: {principal_name}"
                            ),
                        )
                    )
                    change.status = Status.applied
                except Exception as e:
                    log_data["message"] = "Exception occurred attaching managed policy"
                    log_data["error"] = str(e)
                    log.error(log_data, exc_info=True)
                    sentry_sdk.capture_exception()
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=(
                                f"Error occurred attaching managed policy {change.arn} to principal: "
                                "{principal_name}: " + str(e)
                            ),
                        )
                    )
            elif change.action == Action.detach:
                try:
                    if arn_parsed["resource"] == "role":
                        await sync_to_async(iam_client.detach_role_policy)(
                            RoleName=principal_name, PolicyArn=change.arn
                        )
                    elif arn_parsed["resource"] == "user":
                        await sync_to_async(iam_client.detach_user_policy)(
                            UserName=principal_name, PolicyArn=change.arn
                        )
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=(
                                f"Successfully detached managed policy {change.arn} from principal: {principal_name}"
                            ),
                        )
                    )
                    change.status = Status.applied
                except Exception as e:
                    log_data["message"] = "Exception occurred detaching managed policy"
                    log_data["error"] = str(e)
                    log.error(log_data, exc_info=True)
                    sentry_sdk.capture_exception()
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=(
                                f"Error occurred detaching managed policy {change.arn} from principal: "
                                f"{principal_name}: " + str(e)
                            ),
                        )
                    )
        elif change.change_type == "assume_role_policy":
            if arn_parsed["resource"] == "user":
                raise UnsupportedChangeType(
                    "IAM users don't have assume role policies. Unable to process request."
                )
            try:
                await sync_to_async(iam_client.update_assume_role_policy)(
                    RoleName=principal_name,
                    PolicyDocument=json.dumps(
                        change.policy.policy_document, escape_forward_slashes=False
                    ),
                )
                response.action_results.append(
                    ActionResult(
                        status="success",
                        message=f"Successfully updated assume role policy for principal: {principal_name}",
                    )
                )
                change.status = Status.applied
            except Exception as e:
                log_data[
                    "message"
                ] = "Exception occurred updating assume role policy policy"
                log_data["error"] = str(e)
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()
                response.errors += 1
                response.action_results.append(
                    ActionResult(
                        status="error",
                        message=f"Error occurred updating assume role policy for principal: {principal_name}: "
                        + str(e),
                    )
                )
        elif change.change_type == "resource_tag":
            if change.tag_action in [TagAction.create, TagAction.update]:
                if change.original_key and not change.key:
                    change.key = change.original_key
                if change.original_value and not change.value:
                    change.value = change.original_value
                try:
                    if arn_parsed["resource"] == "role":
                        await sync_to_async(iam_client.tag_role)(
                            RoleName=principal_name,
                            Tags=[{"Key": change.key, "Value": change.value}],
                        )
                    elif arn_parsed["resource"] == "user":
                        await sync_to_async(iam_client.tag_user)(
                            UserName=principal_name,
                            Tags=[{"Key": change.key, "Value": change.value}],
                        )
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=f"Successfully created or updated tag for principal: {principal_name}",
                        )
                    )
                    if change.original_key and change.original_key != change.key:
                        if arn_parsed["resource"] == "role":
                            await sync_to_async(iam_client.untag_role)(
                                RoleName=principal_name, TagKeys=[change.original_key]
                            )
                        elif arn_parsed["resource"] == "user":
                            await sync_to_async(iam_client.untag_user)(
                                UserName=principal_name, TagKeys=[change.original_key]
                            )
                        response.action_results.append(
                            ActionResult(
                                status="success",
                                message=f"Successfully renamed tag {change.original_key} to {change.key}.",
                            )
                        )
                    change.status = Status.applied
                except Exception as e:
                    log_data["message"] = "Exception occurred creating or updating tag"
                    log_data["error"] = str(e)
                    log.error(log_data, exc_info=True)
                    sentry_sdk.capture_exception()
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=f"Error occurred updating tag for principal: {principal_name}: "
                            + str(e),
                        )
                    )
            if change.tag_action == TagAction.delete:
                try:
                    if arn_parsed["resource"] == "role":
                        await sync_to_async(iam_client.untag_role)(
                            RoleName=principal_name, TagKeys=[change.key]
                        )
                    elif arn_parsed["resource"] == "user":
                        await sync_to_async(iam_client.untag_user)(
                            UserName=principal_name, TagKeys=[change.key]
                        )
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=f"Successfully deleted tag for principal: {principal_name}",
                        )
                    )
                    change.status = Status.applied
                except Exception as e:
                    log_data["message"] = "Exception occurred deleting tag"
                    log_data["error"] = str(e)
                    log.error(log_data, exc_info=True)
                    sentry_sdk.capture_exception()
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=f"Error occurred deleting tag for principal: {principal_name}: "
                            + str(e),
                        )
                    )
        else:
            # unsupported type for auto-application
            if change.autogenerated and extended_request.admin_auto_approve:
                # If the change was auto-generated and an administrator auto-approved the choices, there's no need
                # to try to apply the auto-generated policies.
                pass
            else:
                response.action_results.append(
                    ActionResult(
                        status="error",
                        message=f"Error occurred applying: Change type {change.change_type} is not supported",
                    )
                )
                response.errors += 1
                log_data["message"] = "Unsupported type for auto-application detected"
                log_data["change"] = change.dict()
                log.error(log_data)

    log_data["message"] = "Finished applying request changes"
    log_data["request"] = extended_request.dict()
    log_data["response"] = response.dict()
    log.info(log_data)


async def populate_old_policies(
    extended_request: ExtendedRequestModel,
    user: str,
    principal: Optional[ExtendedAwsPrincipalModel] = None,
) -> ExtendedRequestModel:
    """
    Populates the old policies for each inline policy.
    Note: Currently only applicable when the principal ARN is a role and for old inline_policies, assume role policy

    :param extended_request: ExtendedRequestModel
    :param user: username
    :return ExtendedRequestModel
    """

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "principal": extended_request.principal,
        "request": extended_request.dict(),
        "message": "Populating old policies",
    }
    log.debug(log_data)

    if extended_request.principal.principal_type == "AwsResource":
        principal_arn = extended_request.principal.principal_arn
        role_account_id = await get_resource_account(principal_arn)
        arn_parsed = parse_arn(principal_arn)

        if arn_parsed["service"] != "iam" or arn_parsed["resource"] not in [
            "role",
            "user",
        ]:
            log_data[
                "message"
            ] = "ARN type not supported for populating old policy changes."
            log.debug(log_data)
            return extended_request

        principal_name = arn_parsed["resource_path"].split("/")[-1]
        if not principal:
            if arn_parsed["resource"] == "role":
                principal = await get_role_details(
                    role_account_id,
                    role_name=principal_name,
                    extended=True,
                    force_refresh=True,
                )
            elif arn_parsed["resource"] == "user":
                principal = await get_user_details(
                    role_account_id,
                    user_name=principal_name,
                    extended=True,
                    force_refresh=True,
                )

    for change in extended_request.changes.changes:
        if change.status == Status.applied:
            # Skip changing any old policies that are saved for historical record (already applied)
            continue
        if change.change_type == "assume_role_policy":
            change.old_policy = PolicyModel(
                policy_sha256=sha256(
                    json.dumps(
                        principal.assume_role_policy_document,
                        escape_forward_slashes=False,
                    ).encode()
                ).hexdigest(),
                policy_document=principal.assume_role_policy_document,
            )
        elif change.change_type == "inline_policy" and not change.new:
            for existing_policy in principal.inline_policies:
                if change.policy_name == existing_policy.get("PolicyName"):
                    change.old_policy = PolicyModel(
                        policy_sha256=sha256(
                            json.dumps(
                                existing_policy.get("PolicyDocument"),
                                escape_forward_slashes=False,
                            ).encode()
                        ).hexdigest(),
                        policy_document=existing_policy.get("PolicyDocument"),
                    )
                    break

    log_data["message"] = "Done populating old policies"
    log_data["request"] = extended_request.dict()
    log.debug(log_data)
    return extended_request


async def populate_old_managed_policies(
    extended_request: ExtendedRequestModel,
    user: str,
) -> Dict:
    """
    Populates the old policies for a managed policy resource change.

    :param extended_request: ExtendedRequestModel
    :param user: username
    :return ExtendedRequestModel
    """

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "principal": extended_request.principal,
        "request": extended_request.dict(),
        "message": "Populating old managed policies",
    }
    log.debug(log_data)
    managed_policy_resource = None
    result = {"changed": False}

    if extended_request.principal.principal_type == "AwsResource":
        principal_arn = extended_request.principal.principal_arn
        arn_parsed = parse_arn(principal_arn)

        if arn_parsed["service"] != "iam" or arn_parsed["resource"] != "policy":
            log_data[
                "message"
            ] = "ARN type not supported for populating old managed policy changes."
            log.debug(log_data)
            return result

        try:
            managed_policy_resource = await sync_to_async(get_managed_policy_document)(
                policy_arn=principal_arn,
                account_number=arn_parsed["account"],
                assume_role=config.get("policies.role_name"),
                region=config.region,
                retry_max_attempts=2,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchEntity":
                # Could be a new managed policy, hence not found, in this case there are no old policies
                return result
            raise
    else:
        # TODO: Add Honeybee Support for editing managed policies
        return result
    for change in extended_request.changes.changes:
        if (
            change.status == Status.applied
            or change.change_type != "managed_policy_resource"
        ):
            # Skip changing any old policies that are saved for historical record (already applied)
            continue
        if managed_policy_resource:
            old_policy_sha256 = sha256(
                json.dumps(
                    managed_policy_resource, escape_forward_slashes=False
                ).encode()
            ).hexdigest()
            if (
                change.old_policy
                and old_policy_sha256 == change.old_policy.policy_sha256
            ):
                # Old policy hasn't changed since last refresh of page, no need to generate resource policy again
                continue

            result["changed"] = True
            change.old_policy = PolicyModel(
                policy_sha256=sha256(
                    json.dumps(
                        managed_policy_resource,
                        escape_forward_slashes=False,
                    ).encode()
                ).hexdigest(),
                policy_document=managed_policy_resource,
            )

    log_data["message"] = "Done populating old managed policies"
    log_data["request"] = extended_request.dict()
    log.debug(log_data)
    result["extended_request"] = extended_request
    return result


async def populate_cross_account_resource_policy_for_change(
    change, extended_request, log_data
):
    resource_policies_changed = False
    supported_resource_policies = config.get(
        "policies.supported_resource_types_for_policy_application", ["s3", "sqs", "sns"]
    )
    sts_resource_policy_supported = config.get(
        "policies.sts_resource_policy_supported", True
    )
    supported_trust_policy_permissions = config.get(
        "policies.supported_trust_policy_permissions",
        [
            "sts:AssumeRole",
            "sts:TagSession",
            "sts:AssumeRoleWithSAML",
            "sts:AssumeRoleWithWebIdentity",
        ],
    )
    all_accounts = await get_account_id_to_name_mapping(status=None)
    default_policy = {"Version": "2012-10-17", "Statement": []}
    if change.status == Status.applied:
        # Skip any changes that have already been applied so we don't overwrite any historical records
        return resource_policies_changed
    if (
        change.change_type == "resource_policy"
        or change.change_type == "sts_resource_policy"
    ):
        # resource policy change or sts assume role policy change
        resource_arn_parsed = parse_arn(change.arn)
        resource_type = resource_arn_parsed["service"]
        resource_name = resource_arn_parsed["resource"]
        resource_region = resource_arn_parsed["region"]
        resource_account = resource_arn_parsed["account"]
        if not resource_account:
            resource_account = await get_resource_account(change.arn)
        if resource_type in supported_resource_policies:
            change.supported = True
        elif (
            change.change_type == "sts_resource_policy"
            and sts_resource_policy_supported
        ):
            change.supported = True
        else:
            change.supported = False

        # If we don't have resource_account (due to resource not being in Config or 3rd Party account),
        # force the change to be not supported and default policy
        if not resource_account:
            change.supported = False
            old_policy = default_policy
            log_data["message"] = "Resource account couldn't be determined"
            log_data["resource_arn"] = change.arn
            log.warning(log_data)
        elif resource_account not in all_accounts.keys():
            # if we see the resource account, but it is not an account that we own
            change.supported = False
            old_policy = default_policy
            log_data[
                "message"
            ] = "Resource account doesn't belong to organization's accounts"
            log_data["resource_arn"] = change.arn
            log.warning(log_data)
        else:
            if change.change_type == "resource_policy":
                old_policy = await get_resource_policy(
                    account=resource_account,
                    resource_type=resource_type,
                    name=resource_name,
                    region=resource_region,
                )
            else:
                role_name = resource_arn_parsed["resource_path"].split("/")[-1]
                role = await get_role_details(
                    resource_account,
                    role_name=role_name,
                    extended=True,
                    force_refresh=True,
                )
                if not role:
                    log.error(
                        {
                            **log_data,
                            "message": (
                                "Unable to retrieve role. Won't attempt to make cross-account policy."
                            ),
                        }
                    )
                    return
                old_policy = role.assume_role_policy_document

        old_policy_sha256 = sha256(
            json.dumps(old_policy, escape_forward_slashes=False).encode()
        ).hexdigest()
        if change.old_policy and old_policy_sha256 == change.old_policy.policy_sha256:
            # Old policy hasn't changed since last refresh of page, no need to generate resource policy again
            return
        # Otherwise it has changed
        resource_policies_changed = True
        change.old_policy = PolicyModel(
            policy_sha256=old_policy_sha256, policy_document=old_policy
        )
        if not change.autogenerated:
            # Change is not autogenerated (user submitted or modified), don't auto-generate
            return resource_policies_changed
        # Have to grab the actions from the source inline change for resource policy changes
        actions = []
        resource_arns = []
        for source_change in extended_request.changes.changes:
            # Find the specific inline policy associated with this change
            if (
                source_change.change_type == "inline_policy"
                and source_change.id == change.source_change_id
            ):
                for statement in source_change.policy.policy_document.get(
                    "Statement", []
                ):
                    # Find the specific statement within the inline policy associated with this resource
                    if change.arn in statement.get("Resource"):
                        statement_actions = statement.get("Action", [])
                        statement_actions = (
                            statement_actions
                            if isinstance(statement_actions, list)
                            else [statement_actions]
                        )
                        for action in statement_actions:
                            if action.startswith(f"{resource_type}:") or (
                                resource_type == "iam" and action.startswith("sts")
                            ):
                                if change.change_type == "sts_resource_policy":
                                    # only supported actions allowed for sts resource policy
                                    if action in supported_trust_policy_permissions:
                                        actions.append(action)
                                else:
                                    actions.append(action)
                        for resource in statement.get("Resource"):
                            if change.arn in resource:
                                resource_arns.append(resource)

        new_policy = await generate_updated_resource_policy(
            existing=old_policy,
            principal_arn=extended_request.principal.principal_arn,
            resource_arns=list(set(resource_arns)),
            actions=actions,
            # since iam assume role policy documents can't include resources
            include_resources=change.change_type == "resource_policy",
        )
        new_policy_sha256 = sha256(
            json.dumps(new_policy, escape_forward_slashes=False).encode()
        ).hexdigest()
        change.policy = PolicyModel(
            policy_sha256=new_policy_sha256, policy_document=new_policy
        )
        return resource_policies_changed


async def populate_cross_account_resource_policies(
    extended_request: ExtendedRequestModel, user: str
) -> Dict:
    """
    Populates the cross-account resource policies for supported resources for each inline policy.
    :param extended_request: ExtendedRequestModel
    :param user: username
    :return: Dict:
        changed: whether the resource policies have changed or not
        extended_request: modified extended_request
    """

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "arn": extended_request.principal.principal_arn,
        "request": extended_request.dict(),
        "message": "Populating cross-account resource policies",
    }
    log.debug(log_data)

    concurrent_tasks = []
    for change in extended_request.changes.changes:
        concurrent_tasks.append(
            populate_cross_account_resource_policy_for_change(
                change, extended_request, log_data
            )
        )
    concurrent_tasks_results = await asyncio.gather(*concurrent_tasks)
    resource_policies_changed = bool(any(concurrent_tasks_results))

    log_data["message"] = "Done populating cross account resource policies"
    log_data["request"] = extended_request.dict()
    log_data["resource_policies_changed"] = resource_policies_changed
    log.debug(log_data)
    return {"changed": resource_policies_changed, "extended_request": extended_request}


async def apply_managed_policy_resource_tag_change(
    extended_request: ExtendedRequestModel,
    change: ResourceTagChangeModel,
    response: PolicyRequestModificationResponseModel,
    user: str,
) -> PolicyRequestModificationResponseModel:
    """
    Applies resource tagging changes for managed policies

    Caution: this method applies changes blindly... meaning it assumes before calling this method,
    you have validated the changes being made are authorized.

    :param change: ResourcePolicyChangeModel
    :param extended_request: ExtendedRequestModel
    :param user: Str - requester's email address
    :param response: RequestCreationResponse

    """
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "change": change.dict(),
        "message": "Applying resource policy change changes",
        "request": extended_request.dict(),
    }
    resource_arn_parsed = parse_arn(change.principal.principal_arn)
    resource_type = resource_arn_parsed["service"]
    resource_name = resource_arn_parsed["resource"]
    resource_account = resource_arn_parsed["account"]
    if not resource_account:
        resource_account = await get_resource_account(change.principal.principal_arn)

    if not resource_account:
        # If we don't have resource_account (due to resource not being in Config or 3rd Party account),
        # we can't apply this change
        log_data["message"] = "Resource account not found"
        log.warning(log_data)
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Cannot apply change to {change.principal.json()} as cannot determine resource account",
            )
        )
        return response

    if resource_type != "iam" or resource_name != "policy" or resource_account == "aws":
        # Not a managed policy, or a managed policy that is AWS owned
        log_data["message"] = "Resource change not supported"
        log.warning(log_data)
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Cannot apply change to {change.principal.json()} as it's not supported",
            )
        )
        return response
    iam_client = await sync_to_async(boto3_cached_conn)(
        "iam",
        service_type="client",
        account_number=resource_account,
        region=config.region,
        assume_role=config.get("policies.role_name"),
        session_name=sanitize_session_name("tag-updater-" + user),
        retry_max_attempts=2,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=config.get(
                "aws.sts_endpoint_url", "https://sts.{region}.amazonaws.com"
            ).format(region=config.region),
        ),
        client_kwargs=config.get("boto3.client_kwargs", {}),
    )
    principal_arn = change.principal.principal_arn
    if change.tag_action in [TagAction.create, TagAction.update]:
        if change.original_key and not change.key:
            change.key = change.original_key
        if change.original_value and not change.value:
            change.value = change.original_value
        try:
            await sync_to_async(iam_client.tag_policy)(
                PolicyArn=principal_arn,
                Tags=[{"Key": change.key, "Value": change.value}],
            )
            response.action_results.append(
                ActionResult(
                    status="success",
                    message=f"Successfully created or updated tag for managed policy: {principal_arn}",
                )
            )
            if change.original_key and change.original_key != change.key:
                await sync_to_async(iam_client.untag_policy)(
                    PolicyArn=principal_arn, TagKeys=[change.original_key]
                )
                response.action_results.append(
                    ActionResult(
                        status="success",
                        message=f"Successfully renamed tag {change.original_key} to {change.key}.",
                    )
                )
            change.status = Status.applied
        except Exception as e:
            log_data["message"] = "Exception occurred creating or updating tag"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            sentry_sdk.capture_exception()
            response.errors += 1
            response.action_results.append(
                ActionResult(
                    status="error",
                    message=f"Error occurred updating tag for managed policy: {principal_arn}: "
                    + str(e),
                )
            )
    elif change.tag_action == TagAction.delete:
        try:
            await sync_to_async(iam_client.untag_policy)(
                PolicyArn=principal_arn, TagKeys=[change.key]
            )
            response.action_results.append(
                ActionResult(
                    status="success",
                    message=f"Successfully deleted tag for managed policy: {principal_arn}",
                )
            )
            change.status = Status.applied
        except Exception as e:
            log_data["message"] = "Exception occurred deleting tag"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            sentry_sdk.capture_exception()
            response.errors += 1
            response.action_results.append(
                ActionResult(
                    status="error",
                    message=f"Error occurred deleting tag for managed policy: {principal_arn}: "
                    + str(e),
                )
            )
    else:
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Unsupport change requested for tag {change.tag_action}",
            )
        )

    return response


async def apply_non_iam_resource_tag_change(
    extended_request: ExtendedRequestModel,
    change: ResourceTagChangeModel,
    response: PolicyRequestModificationResponseModel,
    user: str,
) -> PolicyRequestModificationResponseModel:
    """
    Applies resource tagging changes for supported non IAM role tags

    Caution: this method applies changes blindly... meaning it assumes before calling this method,
    you have validated the changes being made are authorized.

    :param change: ResourcePolicyChangeModel
    :param extended_request: ExtendedRequestModel
    :param user: Str - requester's email address
    :param response: RequestCreationResponse

    """
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "change": change.dict(),
        "message": "Applying resource policy change changes",
        "request": extended_request.dict(),
    }
    resource_arn_parsed = parse_arn(change.principal.principal_arn)
    resource_type = resource_arn_parsed["service"]
    resource_name = resource_arn_parsed["resource"]
    resource_region = resource_arn_parsed["region"]
    resource_account = resource_arn_parsed["account"]
    if not resource_account:
        resource_account = await get_resource_account(change.principal.principal_arn)
    if resource_type == "s3" and not resource_region:
        resource_region = await get_bucket_location_with_fallback(
            resource_name, resource_account
        )

    if not resource_account:
        # If we don't have resource_account (due to resource not being in Config or 3rd Party account),
        # we can't apply this change
        log_data["message"] = "Resource account not found"
        log.warning(log_data)
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Cannot apply change to {change.principal.json()} as cannot determine resource account",
            )
        )
        return response

    supported_resource_types = config.get(
        "policies.supported_resource_types_for_policy_application", ["s3", "sqs", "sns"]
    )

    if resource_type not in supported_resource_types:
        log_data["message"] = "Resource change not supported"
        log.warning(log_data)
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Cannot apply change to {change.principal.json()} as it's not supported",
            )
        )
        return response

    try:
        client = await sync_to_async(boto3_cached_conn)(
            resource_type,
            service_type="client",
            future_expiration_minutes=15,
            account_number=resource_account,
            assume_role=config.get("policies.role_name"),
            region=resource_region or config.region,
            session_name=sanitize_session_name("apply-resource-tag-" + user),
            arn_partition="aws",
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=config.get(
                    "aws.sts_endpoint_url", "https://sts.{region}.amazonaws.com"
                ).format(region=config.region),
            ),
            client_kwargs=config.get("boto3.client_kwargs", {}),
            retry_max_attempts=2,
        )

        resource_details = await fetch_resource_details(
            resource_account,
            resource_type,
            resource_name,
            resource_region or config.region,
        )

        if change.original_key and not change.key:
            change.key = change.original_key
        if change.original_value and not change.value:
            change.value = change.original_value

        if resource_type == "s3":
            if change.tag_action in [TagAction.create, TagAction.update]:
                tag_key_preexists = False
                resulting_tagset = []
                for tag in resource_details["TagSet"]:
                    # If we renamed a tag key, let's "skip" the tag with the original name
                    if change.original_key and change.original_key != change.key:
                        if tag.get("Key") == change.original_key:
                            continue
                    if change.key == tag["Key"]:
                        tag_key_preexists = True
                        # If we changed the value of an existing tag, let's record that
                        resulting_tagset.append(
                            {"Key": change.key, "Value": change.value}
                        )
                    else:
                        # Leave original tag unmodified
                        resulting_tagset.append(tag)

                # Let's create the tag if it is a new one
                if not tag_key_preexists:
                    resulting_tagset.append({"Key": change.key, "Value": change.value})

                await sync_to_async(client.put_bucket_tagging)(
                    Bucket=resource_name,
                    Tagging={"TagSet": resulting_tagset},
                )

            elif change.tag_action == TagAction.delete:
                resulting_tagset = []

                for tag in resource_details["TagSet"]:
                    if tag.get("Key") != change.key:
                        resulting_tagset.append(tag)

                resource_details["TagSet"] = resulting_tagset
                await sync_to_async(client.put_bucket_tagging)(
                    Bucket=resource_name,
                    Tagging={"TagSet": resource_details["TagSet"]},
                )
        elif resource_type == "sns":
            if change.tag_action in [TagAction.create, TagAction.update]:
                await sync_to_async(client.tag_resource)(
                    ResourceArn=change.principal.principal_arn,
                    Tags=[{"Key": change.key, "Value": change.value}],
                )
                # Renaming a key
                if change.original_key and change.original_key != change.key:
                    await sync_to_async(client.untag_resource)(
                        ResourceArn=change.principal.principal_arn,
                        TagKeys=[change.original_key],
                    )
            elif change.tag_action == TagAction.delete:
                await sync_to_async(client.untag_resource)(
                    ResourceArn=change.principal.principal_arn,
                    TagKeys=[change.key],
                )
        elif resource_type == "sqs":
            if change.tag_action in [TagAction.create, TagAction.update]:
                await sync_to_async(client.tag_queue)(
                    QueueUrl=resource_details["QueueUrl"],
                    Tags={change.key: change.value},
                )
                # Renaming a key
                if change.original_key and change.original_key != change.key:
                    await sync_to_async(client.untag_queue)(
                        QueueUrl=resource_details["QueueUrl"],
                        TagKeys=[change.original_key],
                    )
            elif change.tag_action == TagAction.delete:
                await sync_to_async(client.untag_queue)(
                    QueueUrl=resource_details["QueueUrl"], TagKeys=[change.key]
                )
        response.action_results.append(
            ActionResult(
                status="success",
                message=f"Successfully updated resource policy for {change.principal.principal_arn}",
            )
        )
        change.status = Status.applied

    except Exception as e:
        log_data["message"] = "Exception changing resource tags"
        log_data["error"] = str(e)
        log.error(log_data, exc_info=True)
        sentry_sdk.capture_exception()
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Error occurred changing resource tags for {change.principal.principal_arn}"
                + str(e),
            )
        )

    log_data["message"] = "Finished applying resource tagging change"
    log_data["response"] = response.dict()
    log_data["request"] = extended_request.dict()
    log_data["change"] = change.dict()
    log.debug(log_data)
    return response


async def apply_managed_policy_resource_change(
    extended_request: ExtendedRequestModel,
    change: ManagedPolicyResourceChangeModel,
    response: PolicyRequestModificationResponseModel,
    user: str,
) -> PolicyRequestModificationResponseModel:
    """
    Applies resource policy change for managed policies

    Caution: this method applies changes blindly... meaning it assumes before calling this method,
    you have validated the changes being made are authorized.

    :param change: ResourcePolicyChangeModel
    :param extended_request: ExtendedRequestModel
    :param user: Str - requester's email address
    :param response: RequestCreationResponse

    """

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "change": change.dict(),
        "message": "Applying managed policy resource change",
        "request": extended_request.dict(),
    }
    log.info(log_data)

    arn_parsed = parse_arn(extended_request.principal.principal_arn)
    resource_type = arn_parsed["service"]
    resource_name = arn_parsed["resource"]
    resource_account = arn_parsed["account"]
    if resource_type != "iam" or resource_name != "policy" or resource_account == "aws":
        log_data[
            "message"
        ] = "ARN type not supported for managed policy resource changes."
        log.error(log_data)
        response.errors += 1
        response.action_results.append(
            ActionResult(status="error", message=log_data["message"])
        )
        return response

    if not resource_account:
        # If we don't have resource_account (due to resource not being in Config or 3rd Party account),
        # we can't apply this change
        log_data["message"] = "Resource account not found"
        log.warning(log_data)
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Cannot apply change to {extended_request.principal.principal_arn} as cannot determine resource account",
            )
        )
        return response

    conn_details = {
        "account_number": resource_account,
        "assume_role": config.get("policies.role_name"),
        "session_name": f"ConsoleMe_MP_{user}",
        "client_kwargs": config.get("boto3.client_kwargs", {}),
    }

    # Save current policy by populating "old" policies at the time of application for historical record
    populate_old_managed_policies_results = await populate_old_managed_policies(
        extended_request, user
    )
    if populate_old_managed_policies_results["changed"]:
        extended_request = populate_old_managed_policies_results["extended_request"]

    policy_name = arn_parsed["resource_path"].split("/")[-1]
    if change.new:
        description = f"Managed Policy created using ConsoleMe by {user}"
        # create new policy
        try:
            policy_path = "/" + arn_parsed["resource_path"].replace(policy_name, "")
            await create_or_update_managed_policy(
                new_policy=change.policy.policy_document,
                policy_name=policy_name,
                policy_arn=extended_request.principal.principal_arn,
                description=description,
                policy_path=policy_path,
                **conn_details,
            )
            response.action_results.append(
                ActionResult(
                    status="success",
                    message=f"Successfully created managed policy {extended_request.principal.principal_arn}",
                )
            )
            change.status = Status.applied
        except Exception as e:
            log_data["message"] = "Exception occurred creating managed policy"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            sentry_sdk.capture_exception()
            response.errors += 1
            response.action_results.append(
                ActionResult(
                    status="error",
                    message=f"Error occurred creating managed policy: {str(e)}",
                )
            )
    else:
        try:
            await create_or_update_managed_policy(
                new_policy=change.policy.policy_document,
                policy_name=policy_name,
                policy_arn=extended_request.principal.principal_arn,
                description="",
                existing_policy=True,
                **conn_details,
            )
            response.action_results.append(
                ActionResult(
                    status="success",
                    message=f"Successfully updated managed policy {extended_request.principal.principal_arn}",
                )
            )
            change.status = Status.applied
        except Exception as e:
            log_data["message"] = "Exception occurred updating managed policy"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            sentry_sdk.capture_exception()
            response.errors += 1
            response.action_results.append(
                ActionResult(
                    status="error",
                    message=f"Error occurred creating updating policy: {str(e)}",
                )
            )
    return response


async def apply_resource_policy_change(
    extended_request: ExtendedRequestModel,
    change: ResourcePolicyChangeModel,
    response: PolicyRequestModificationResponseModel,
    user: str,
) -> PolicyRequestModificationResponseModel:
    """
    Applies resource policy change for supported changes

    Caution: this method applies changes blindly... meaning it assumes before calling this method,
    you have validated the changes being made are authorized.

    :param change: ResourcePolicyChangeModel
    :param extended_request: ExtendedRequestModel
    :param user: Str - requester's email address
    :param response: RequestCreationResponse

    """

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "change": change.dict(),
        "message": "Applying resource policy change changes",
        "request": extended_request.dict(),
    }
    log.info(log_data)

    resource_arn_parsed = parse_arn(change.arn)
    resource_type = resource_arn_parsed["service"]
    resource_name = resource_arn_parsed["resource"]
    resource_region = resource_arn_parsed["region"]
    resource_account = resource_arn_parsed["account"]
    if not resource_account:
        resource_account = await get_resource_account(change.arn)
    if resource_type == "s3" and not resource_region:
        resource_region = await get_bucket_location_with_fallback(
            resource_name, resource_account
        )

    if not resource_account:
        # If we don't have resource_account (due to resource not being in Config or 3rd Party account),
        # we can't apply this change
        log_data["message"] = "Resource account not found"
        log.warning(log_data)
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Cannot apply change to {change.arn} as cannot determine resource account",
            )
        )
        return response

    supported_resource_types = config.get(
        "policies.supported_resource_types_for_policy_application", ["s3", "sqs", "sns"]
    )
    sts_resource_policy_supported = config.get(
        "policies.sts_resource_policy_supported", True
    )

    if (
        not change.supported
        or (
            change.change_type == "resource_policy"
            and resource_type not in supported_resource_types
        )
        or (
            change.change_type == "sts_resource_policy"
            and not sts_resource_policy_supported
        )
    ):
        log_data["message"] = "Resource change not supported"
        log.warning(log_data)
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Cannot apply change to {change.arn} as it's not supported",
            )
        )
        return response

    try:
        client = await sync_to_async(boto3_cached_conn)(
            resource_type,
            service_type="client",
            future_expiration_minutes=15,
            account_number=resource_account,
            assume_role=config.get("policies.role_name"),
            region=resource_region or config.region,
            session_name=sanitize_session_name("apply-resource-policy-" + user),
            arn_partition="aws",
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=config.get(
                    "aws.sts_endpoint_url", "https://sts.{region}.amazonaws.com"
                ).format(region=config.region),
            ),
            client_kwargs=config.get("boto3.client_kwargs", {}),
            retry_max_attempts=2,
        )
        if resource_type == "s3":
            await sync_to_async(client.put_bucket_policy)(
                Bucket=resource_name,
                Policy=json.dumps(
                    change.policy.policy_document, escape_forward_slashes=False
                ),
            )
        elif resource_type == "sns":
            await sync_to_async(client.set_topic_attributes)(
                TopicArn=change.arn,
                AttributeName="Policy",
                AttributeValue=json.dumps(
                    change.policy.policy_document, escape_forward_slashes=False
                ),
            )
        elif resource_type == "sqs":
            queue_url: dict = await sync_to_async(client.get_queue_url)(
                QueueName=resource_name
            )
            await sync_to_async(client.set_queue_attributes)(
                QueueUrl=queue_url.get("QueueUrl"),
                Attributes={
                    "Policy": json.dumps(
                        change.policy.policy_document, escape_forward_slashes=False
                    )
                },
            )
        elif resource_type == "iam":
            role_name = resource_arn_parsed["resource_path"].split("/")[-1]
            await sync_to_async(client.update_assume_role_policy)(
                RoleName=role_name,
                PolicyDocument=json.dumps(
                    change.policy.policy_document, escape_forward_slashes=False
                ),
            )
            # force refresh the role for which we just changed the assume role policy doc
            await aws.fetch_iam_role(resource_account, change.arn, force_refresh=True)
        response.action_results.append(
            ActionResult(
                status="success",
                message=f"Successfully updated resource policy for {change.arn}",
            )
        )
        change.status = Status.applied

    except Exception as e:
        log_data["message"] = "Exception occurred updating resource policy"
        log_data["error"] = str(e)
        log.error(log_data, exc_info=True)
        sentry_sdk.capture_exception()
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Error occurred updating resource policy for {change.arn}"
                + str(e),
            )
        )

    log_data["message"] = "Finished applying resource policy change"
    log_data["response"] = response.dict()
    log_data["request"] = extended_request.dict()
    log_data["change"] = change.dict()
    log.debug(log_data)
    return response


async def _add_error_to_response(
    log_data: Dict,
    response: PolicyRequestModificationResponseModel,
    message: str,
    error=None,
):
    log_data["message"] = message
    log_data["error"] = error
    log.error(log_data)
    response.errors += 1
    response.action_results.append(
        ActionResult(status="error", message=log_data["message"])
    )
    return response


async def _update_dynamo_with_change(
    user: str,
    extended_request: ExtendedRequestModel,
    log_data: Dict,
    response: PolicyRequestModificationResponseModel,
    success_message: str,
    error_message: str,
    visible: bool = True,
):
    dynamo = UserDynamoHandler(user)
    try:
        await dynamo.write_policy_request_v2(extended_request)
        response.action_results.append(
            ActionResult(status="success", message=success_message, visible=visible)
        )
    except Exception as e:
        log_data["message"] = error_message
        log_data["error"] = str(e)
        log.error(log_data, exc_info=True)
        sentry_sdk.capture_exception()
        response.errors += 1
        response.action_results.append(
            ActionResult(status="error", message=error_message + ": " + str(e))
        )
    return response


async def _get_specific_change(changes: ChangeModelArray, change_id: str):
    for change in changes.changes:
        if change.id == change_id:
            return change

    return None


async def maybe_approve_reject_request(
    extended_request: ExtendedRequestModel,
    user: str,
    log_data: Dict,
    response: PolicyRequestModificationResponseModel,
) -> PolicyRequestModificationResponseModel:
    any_changes_applied = False
    any_changes_pending = False
    any_changes_cancelled = False
    request_status_changed = False

    for change in extended_request.changes.changes:
        if change.status == Status.applied:
            any_changes_applied = True
        if change.status == Status.not_applied:
            # Don't consider "unsupported" resource policies as "pending", since they can't be applied.
            if (
                change.change_type == "resource_policy"
                or change.change_type == "sts_resource_policy"
            ) and change.supported is False:
                continue
            # Requests should still be marked as approved if they have pending autogenerated changes
            if change.autogenerated:
                continue
            any_changes_pending = True
        if change.status == Status.cancelled:
            any_changes_cancelled = True
    # Automatically mark request as "approved" if at least one of the changes in the request is approved, and
    # nothing else is pending
    if any_changes_applied and not any_changes_pending:
        extended_request.request_status = RequestStatus.approved
        request_status_changed = True

    # Automatically mark request as "cancelled" if all changes in the request are cancelled
    if not any_changes_applied and not any_changes_pending and any_changes_cancelled:
        extended_request.request_status = RequestStatus.cancelled
        request_status_changed = True
    if request_status_changed:
        extended_request.reviewer = user
        response = await _update_dynamo_with_change(
            user,
            extended_request,
            log_data,
            response,
            "Successfully updated request status",
            "Error updating request in dynamo",
            visible=False,
        )
        await send_communications_policy_change_request_v2(extended_request)
        account_id = await get_resource_account(
            extended_request.principal.principal_arn
        )
        if extended_request.principal.principal_arn.startswith("aws:aws:iam::"):
            await aws.fetch_iam_role(
                account_id, extended_request.principal.principal_arn, force_refresh=True
            )
    return response


async def parse_and_apply_policy_request_modification(
    extended_request: ExtendedRequestModel,
    policy_request_model: PolicyRequestModificationRequestModel,
    user: str,
    user_groups,
    last_updated,
    approval_probe_approved=False,
) -> PolicyRequestModificationResponseModel:
    """
    Parses the policy request modification changes

    :param extended_request: ExtendedRequestModel
    :param user: Str - requester's email address
    :param policy_request_model: PolicyRequestModificationRequestModel
    :param user_groups:  user's groups
    :param last_updated:
    :param approval_probe_approved: Whether this change was approved by an auto-approval probe. If not, user needs to be
        authorized to make the change.
    :return PolicyRequestModificationResponseModel
    """

    log_data: Dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "request": extended_request.dict(),
        "request_changes": policy_request_model.dict(),
        "message": "Parsing request modification changes",
    }
    log.debug(log_data)

    response = PolicyRequestModificationResponseModel(errors=0, action_results=[])
    request_changes = policy_request_model.modification_model

    if request_changes.command in [Command.update_change, Command.cancel_request]:
        can_update_cancel = await can_update_cancel_requests_v2(
            extended_request.requester_email, user, user_groups
        )
        if not can_update_cancel:
            raise Unauthorized(
                "You are not authorized to update or cancel changes in this request"
            )

    if request_changes.command in [
        Command.apply_change,
        Command.approve_request,
        Command.reject_request,
    ]:
        can_manage_policy_request = can_admin_policies(user, user_groups)
        # Authorization required if the policy wasn't approved by an auto-approval probe.
        should_apply_because_auto_approved = (
            request_changes.command == Command.apply_change and approval_probe_approved
        )

        if not can_manage_policy_request and not should_apply_because_auto_approved:
            raise Unauthorized("You are not authorized to manage this request")

    if request_changes.command == Command.move_back_to_pending:
        can_move_back_to_pending = await can_move_back_to_pending_v2(
            extended_request, last_updated, user, user_groups
        )
        if not can_move_back_to_pending:
            raise Unauthorized("Cannot move this request back to pending")

    # If here, then the person is authorized to make the change they want

    # For cancelled / rejected requests, only moving back to pending, adding comments is permitted
    if extended_request.request_status in [
        RequestStatus.cancelled,
        RequestStatus.rejected,
    ] and request_changes.command not in [
        Command.add_comment,
        Command.move_back_to_pending,
    ]:
        raise InvalidRequestParameter(
            f"Cannot perform {request_changes.command.value} on "
            f"{extended_request.request_status.value} requests"
        )

    if request_changes.command == Command.add_comment:
        # TODO: max comment size? prevent spamming?
        comment_model = CommentRequestModificationModel.parse_obj(request_changes)
        user_comment = CommentModel(
            id=str(uuid.uuid4()),
            timestamp=int(time.time()),
            user_email=user,
            user=UserModel(
                email=user,
                extended_info=await auth.get_user_info(user),
                details_url=config.config_plugin().get_employee_info_url(user),
                photo_url=config.config_plugin().get_employee_photo_url(user),
            ),
            last_modified=int(time.time()),
            text=comment_model.comment_text,
        )
        extended_request.comments.append(user_comment)
        success_message = "Successfully added comment"
        error_message = "Error occurred adding comment"
        response = await _update_dynamo_with_change(
            user, extended_request, log_data, response, success_message, error_message
        )
        if user == extended_request.requester_email:
            # User who created the request adding a comment, notification should go to reviewers
            await send_communications_new_comment(extended_request, user)
        else:
            # A reviewer or someone else making the comment, notification should go to original requester
            await send_communications_new_comment(
                extended_request, user, to_addresses=[extended_request.requester_email]
            )

    elif request_changes.command == Command.update_change:
        update_change_model = UpdateChangeModificationModel.parse_obj(request_changes)
        specific_change = await _get_specific_change(
            extended_request.changes, update_change_model.change_id
        )
        # We only support updating inline policies, assume role policy documents and resource policies that haven't
        # applied already
        if (
            specific_change
            and specific_change.change_type
            in [
                "inline_policy",
                "resource_policy",
                "sts_resource_policy",
                "assume_role_policy",
                "managed_policy_resource",
            ]
            and specific_change.status == Status.not_applied
        ):
            specific_change.policy.policy_document = update_change_model.policy_document
            if (
                specific_change.change_type == "resource_policy"
                or specific_change.change_type == "sts_resource_policy"
            ):
                # Special case, if it's autogenerated and a user modifies it, update status to
                # not autogenerated, so we don't overwrite it on page refresh
                specific_change.autogenerated = False
            success_message = "Successfully updated policy document"
            error_message = "Error occurred updating policy document"
            specific_change.updated_by = user
            response = await _update_dynamo_with_change(
                user,
                extended_request,
                log_data,
                response,
                success_message,
                error_message,
            )
        else:
            raise NoMatchingRequest(
                "Unable to find a compatible non-applied change with "
                "that ID in this policy request"
            )

    elif request_changes.command == Command.apply_change:
        apply_change_model = ApplyChangeModificationModel.parse_obj(request_changes)
        specific_change = await _get_specific_change(
            extended_request.changes, apply_change_model.change_id
        )
        if specific_change and specific_change.status == Status.not_applied:
            # Update the policy doc locally for supported changes, if it needs to be updated
            if apply_change_model.policy_document and specific_change.change_type in [
                "inline_policy",
                "resource_policy",
                "sts_resource_policy",
                "assume_role_policy",
                "managed_policy_resource",
            ]:
                specific_change.policy.policy_document = (
                    apply_change_model.policy_document
                )
            managed_policy_arn_regex = re.compile(r"^arn:aws:iam::\d{12}:policy/.+")
            if (
                specific_change.change_type == "resource_policy"
                or specific_change.change_type == "sts_resource_policy"
            ):
                response = await apply_resource_policy_change(
                    extended_request, specific_change, response, user
                )
            elif (
                specific_change.change_type == "resource_tag"
                and not specific_change.principal.principal_arn.startswith(
                    "arn:aws:iam::"
                )
            ):
                response = await apply_non_iam_resource_tag_change(
                    extended_request, specific_change, response, user
                )
            elif (
                specific_change.change_type == "resource_tag"
                and managed_policy_arn_regex.search(
                    specific_change.principal.principal_arn
                )
            ):
                response = await apply_managed_policy_resource_tag_change(
                    extended_request, specific_change, response, user
                )
            elif specific_change.change_type == "managed_policy_resource":
                response = await apply_managed_policy_resource_change(
                    extended_request, specific_change, response, user
                )
            else:
                # Save current policy by populating "old" policies at the time of application for historical record
                extended_request = await populate_old_policies(extended_request, user)
                await apply_changes_to_role(
                    extended_request, response, user, specific_change.id
                )
                account_id = await get_resource_account(
                    extended_request.principal.principal_arn
                )
                await aws.fetch_iam_role(
                    account_id,
                    extended_request.principal.principal_arn,
                    force_refresh=True,
                )
            if specific_change.status == Status.applied:
                # Change was successful, update in dynamo
                success_message = "Successfully updated change in dynamo"
                error_message = "Error updating change in dynamo"
                specific_change.updated_by = user
                response = await _update_dynamo_with_change(
                    user,
                    extended_request,
                    log_data,
                    response,
                    success_message,
                    error_message,
                    visible=False,
                )
        else:
            raise NoMatchingRequest(
                "Unable to find a compatible non-applied change with "
                "that ID in this policy request"
            )

    elif request_changes.command == Command.cancel_change:
        cancel_change_model = CancelChangeModificationModel.parse_obj(request_changes)
        specific_change = await _get_specific_change(
            extended_request.changes, cancel_change_model.change_id
        )
        if specific_change and specific_change.status == Status.not_applied:
            # Update the status
            specific_change.status = Status.cancelled
            specific_change.updated_by = user
            # Update in dynamo
            success_message = "Successfully updated change in dynamo"
            error_message = "Error updating change in dynamo"
            response = await _update_dynamo_with_change(
                user,
                extended_request,
                log_data,
                response,
                success_message,
                error_message,
                visible=False,
            )
        else:
            raise NoMatchingRequest(
                "Unable to find a compatible non-applied change with "
                "that ID in this policy request"
            )

    elif request_changes.command == Command.cancel_request:
        if extended_request.request_status != RequestStatus.pending:
            raise InvalidRequestParameter(
                "Request cannot be cancelled as it's status "
                f"is {extended_request.request_status.value}"
            )
        for change in extended_request.changes.changes:
            if change.status == Status.applied:
                response.errors += 1
                response.action_results.append(
                    ActionResult(
                        status="error",
                        message=(
                            "Request cannot be cancelled because at least one change has been applied already. "
                            "Please apply or cancel the other changes."
                        ),
                    )
                )
                response = await maybe_approve_reject_request(
                    extended_request, user, log_data, response
                )
                return response

        extended_request.request_status = RequestStatus.cancelled
        success_message = "Successfully cancelled request"
        error_message = "Error cancelling request"
        extended_request.reviewer = user
        response = await _update_dynamo_with_change(
            user, extended_request, log_data, response, success_message, error_message
        )
        await send_communications_policy_change_request_v2(extended_request)

    elif request_changes.command == Command.reject_request:
        if extended_request.request_status != RequestStatus.pending:
            raise InvalidRequestParameter(
                f"Request cannot be rejected "
                f"as it's status is {extended_request.request_status.value}"
            )
        for change in extended_request.changes.changes:
            if change.status == Status.applied:
                response.errors += 1
                response.action_results.append(
                    ActionResult(
                        status="error",
                        message=(
                            "Request cannot be rejected because at least one change has been applied already. "
                            "Please apply or cancel the other changes."
                        ),
                    )
                )
                response = await maybe_approve_reject_request(
                    extended_request, user, log_data, response
                )
                return response

        extended_request.request_status = RequestStatus.rejected
        success_message = "Successfully rejected request"
        error_message = "Error rejected request"
        extended_request.reviewer = user
        response = await _update_dynamo_with_change(
            user, extended_request, log_data, response, success_message, error_message
        )
        await send_communications_policy_change_request_v2(extended_request)

    elif request_changes.command == Command.move_back_to_pending:
        extended_request.request_status = RequestStatus.pending
        success_message = "Successfully moved request back to pending"
        error_message = "Error moving request back to pending"
        response = await _update_dynamo_with_change(
            user, extended_request, log_data, response, success_message, error_message
        )

    # This marks a request as complete. This essentially means that all necessary actions have been taken with the
    # request, and doesn't apply any changes.
    elif request_changes.command == Command.approve_request:
        if extended_request.request_status != RequestStatus.pending:
            raise InvalidRequestParameter(
                "Request cannot be approved as it's "
                f"status is {extended_request.request_status.value}"
            )

        # Save current policy by populating "old" policies at the time of application for historical record
        extended_request = await populate_old_policies(extended_request, user)
        extended_request.request_status = RequestStatus.approved
        extended_request.reviewer = user

        success_message = "Successfully updated request status"
        error_message = "Error updating request in dynamo"

        response = await _update_dynamo_with_change(
            user,
            extended_request,
            log_data,
            response,
            success_message,
            error_message,
            visible=False,
        )
        await send_communications_policy_change_request_v2(extended_request)
        account_id = await get_resource_account(
            extended_request.principal.principal_arn
        )
        await aws.fetch_iam_role(
            account_id, extended_request.principal.principal_arn, force_refresh=True
        )

    response = await maybe_approve_reject_request(
        extended_request, user, log_data, response
    )

    log_data["message"] = "Done parsing/applying request modification changes"
    log_data["request"] = extended_request.dict()
    log_data["response"] = response.dict()
    log_data["error"] = None
    log.debug(log_data)
    return response


async def get_resources_from_policy_change(change: ChangeModel):
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

    accounts_d: dict = await get_account_id_to_name_mapping()
    resource_actions: List = []
    if change.change_type not in ["inline_policy"]:
        return []
    policy_document = change.policy.policy_document
    for statement in policy_document.get("Statement", []):
        resources = statement.get("Resource", [])
        resources = resources if isinstance(resources, list) else [resources]
        for resource in resources:
            # We can't yet generate multiple cross-account resource policies
            # based on a partial wildcard in a resource name
            if "*" in resource:
                continue
            if not resource:
                raise Exception(
                    "One or more resources must be specified in the policy."
                )
            resource_name = get_resource_from_arn(resource)
            resource_action = {
                "arn": resource,
                "name": resource_name,
                "account_id": await get_resource_account(resource),
                "region": get_region_from_arn(resource),
                "resource_type": get_service_from_arn(resource),
            }

            resource_action["account_name"] = accounts_d.get(
                resource_action["account_id"]
            )
            resource_action["actions"] = get_actions_for_resource(resource, statement)
            resource_actions.append(ResourceModel.parse_obj(resource_action))
    return resource_actions


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
            if (
                get_service_from_action(action) == resource_service
                or action.lower() == "sts:assumerole"
                and resource_service == "iam"
            ):
                if action not in results:
                    results.append(action)

    return results

import sys
import time
import uuid
from hashlib import sha256

import ujson as json
from policy_sentry.util.arns import parse_arn

from consoleme.config import config
from consoleme.exceptions.exceptions import InvalidRequestParameter
from consoleme.lib.aws import get_resource_account
from consoleme.lib.policies import invalid_characters_in_policy
from consoleme.lib.v2.roles import get_role_details
from consoleme.models import (
    Action,
    ChangeModelArray,
    ChangeType,
    ExtendedRequestModel,
    ExtendedRoleModel,
    InlinePolicyChangeModel,
    ManagedPolicyChangeModel,
    PolicyModel,
    RequestCreationModel,
    ResourceModel,
    ResourcePolicyChangeModel,
    Status,
    UserModel,
)

log = config.get_logger()


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
        "request": request_creation,
        "message": "Incoming request",
    }
    log.info(log_data)

    primary_principal_arn = None
    change_models = request_creation.changes
    if len(change_models.changes) < 1:
        log_data["message"] = "Atleast 1 change is required to create a request."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    inline_policy_changes = []
    managed_policy_changes = []
    resource_policy_changes = []

    for change in change_models.changes:
        # Enforce a maximum of one principal ARN per ChangeGeneratorModelArray (aka Policy Request)
        if not primary_principal_arn:
            primary_principal_arn = change.principal_arn
        if primary_principal_arn != change.principal_arn:
            log_data[
                "message"
            ] = "We only support making changes to a single principal ARN per request."
            log.error(log_data)
            raise InvalidRequestParameter(log_data["message"])

        if change.change_type == ChangeType.inline_policy:
            inline_policy_changes.append(change)
        elif change.change_type == ChangeType.managed_policy:
            managed_policy_changes.append(change)
        elif change.change_type == ChangeType.resource_policy:
            resource_policy_changes.append(change)

        # All changes status must be not-applied at request creation
        change.status = Status.not_applied

    # Make sure the requester is only ever 64 chars with domain
    if len(user) > 64:
        split_items: list = user.split("@")
        user: str = split_items[0][
            : (64 - (len(split_items[-1]) + 1))
        ] + "@" + split_items[-1]

    account_id = await get_resource_account(primary_principal_arn)
    arn_parsed = parse_arn(primary_principal_arn)

    if len(inline_policy_changes) > 0 or len(managed_policy_changes) > 0:
        # for inline policies and managed policies, principal arn must be a role
        if arn_parsed["service"] != "iam" or arn_parsed["resource"] != "role":
            log_data[
                "message"
            ] = "ARN type not supported for inline/managed policy changes."
            log.error(log_data)
            raise InvalidRequestParameter(log_data["message"])
        role_name = arn_parsed["resource_path"].split("/")[-1]
        role = await get_role_details(account_id, role_name=role_name, extended=True)
        for inline_policy_change in inline_policy_changes:
            await validate_inline_policy_change(inline_policy_change, user, role)
        for managed_policy_change in managed_policy_changes:
            await validate_managed_policy_change(managed_policy_change, user, role)

    # TODO: do actual resource policy logic, rather than just the blank stub
    resource_policy = {"Version": "2012-10-17", "Statement": []}
    resource_policy_sha = sha256(json.dumps(resource_policy).encode()).hexdigest()
    primary_principal_resource_model = ResourceModel(
        arn=primary_principal_arn,
        name=arn_parsed["resource_path"].split("/")[-1],
        account_id=account_id,
        resource_type=arn_parsed["service"],
    )

    # Create resource policy stubs for current resources that are used
    for inline_policy_change in inline_policy_changes:
        for resource in inline_policy_change.resources:
            resource_account_id = await get_resource_account(resource.arn)
            if resource_account_id != account_id:
                resource_policy_changes.append(
                    ResourcePolicyChangeModel(
                        arn=resource.arn,
                        policy=PolicyModel(
                            policy_document=resource_policy,
                            policy_sha256=resource_policy_sha,
                        ),
                        change_type=ChangeType.resource_policy,
                        principal_arn=primary_principal_arn,
                        status=Status.not_applied,
                        resources=[primary_principal_resource_model],
                    )
                )

    # TODO: assume role policy document for roles: new model?
    # If here, request is valid and can successfully be generated
    request_changes = ChangeModelArray(
        changes=inline_policy_changes + managed_policy_changes + resource_policy_changes
    )
    return ExtendedRequestModel(
        id=str(uuid.uuid4()),
        arn=primary_principal_arn,
        timestamp=int(time.time()),
        justification=request_creation.justification,
        requester_email=user,
        approvers=[],  # TODO: approvers logic (future feature)
        status="pending",
        changes=request_changes,
        requester_info=UserModel(email=user),
        comments=[],
    )


async def validate_inline_policy_change(
    change: InlinePolicyChangeModel, user: str, role: ExtendedRoleModel
):
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "arn": change.principal_arn,
        "request": change,
        "message": "Validating inline policy change",
    }
    log.info(log_data)
    if await invalid_characters_in_policy(
        change.policy.policy_document
    ) or await invalid_characters_in_policy(change.policy_name):
        log_data["message"] = "Invalid characters were detected in the policy."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    for existing_policy in role.inline_policies:
        # Check if a new policy is being created, ensure that we don't overwrite another policy with same name
        if change.new and change.policy_name == existing_policy.get("PolicyName"):
            log_data["message"] = "Inline Policy with that name already exists."
            log.error(log_data)
            raise InvalidRequestParameter(log_data["message"])
        # Check if policy being updated is the same as existing policy.
        if not change.new and change.policy_name == existing_policy.get("PolicyName"):
            log_data[
                "message"
            ] = "No changes were found between the updated and existing policy."
            log.error(log_data)
            raise InvalidRequestParameter(log_data["message"])

    # TODO: check sha in the request (future feature)
    # If here, then that means inline policy is validated


async def validate_managed_policy_change(
    change: ManagedPolicyChangeModel, user: str, role: ExtendedRoleModel
):
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "arn": change.principal_arn,
        "request": change,
        "message": "Validating managed policy change",
    }
    log.info(log_data)
    if await invalid_characters_in_policy(change.policy_name):
        log_data["message"] = "Invalid characters were detected in the policy name."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])
    if change.action == Action.attach:
        # check to make sure managed policy is not already attached
        for existing_policy in role.managed_policies:
            if change.policy_name == existing_policy.get("PolicyName"):
                log_data[
                    "message"
                ] = "Managed Policy with that name already attached to this role."
                log.error(log_data)
                raise InvalidRequestParameter(log_data["message"])
    elif change.action == Action.detach:
        # check to make sure managed policy is actually attached to role
        seen = False
        for existing_policy in role.managed_policies:
            if change.policy_name == existing_policy.get("PolicyName"):
                seen = True
                break
        if not seen:
            log_data[
                "message"
            ] = "The Managed Policy you are trying to detach is not attached to this role."
            log.error(log_data)
            raise InvalidRequestParameter(log_data["message"])

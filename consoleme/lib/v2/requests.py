import sys
import time
import uuid
from hashlib import sha256

import ujson as json
from asgiref.sync import sync_to_async
from cloudaux.aws.sts import boto3_cached_conn
from policy_sentry.util.arns import parse_arn

from consoleme.config import config
from consoleme.exceptions.exceptions import InvalidRequestParameter
from consoleme.lib.aws import (
    get_resource_account,
    get_resource_policy,
    update_resource_policy,
)
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.policies import invalid_characters_in_policy
from consoleme.lib.v2.roles import get_role_details
from consoleme.models import (
    Action,
    Action1,
    ActionResult,
    AssumeRolePolicyChangeModel,
    ChangeModelArray,
    ChangeType,
    ExtendedRequestModel,
    ExtendedRoleModel,
    InlinePolicyChangeModel,
    ManagedPolicyChangeModel,
    PolicyModel,
    RequestCreationModel,
    RequestCreationResponse,
    ResourceModel,
    ResourcePolicyChangeModel,
    Status,
    UserModel,
)

log = config.get_logger()
auth = get_plugin_by_name(config.get("plugins.auth"))()


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

    primary_principal_arn = None
    change_models = request_creation.changes
    if len(change_models.changes) < 1:
        log_data["message"] = "Atleast 1 change is required to create a request."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    inline_policy_changes = []
    managed_policy_changes = []
    resource_policy_changes = []
    assume_role_policy_changes = []

    extended_request_uuid = str(uuid.uuid4())
    incremental_change_id = 0

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
            change.autogenerated = False
            change.sourceChangeID = None
            # Currently we don't support resource policy changes submitted by customer
            # TODO: change to True when we add support for these
            change.supported = False
            resource_policy_changes.append(change)
        elif change.change_type == ChangeType.assume_role_policy:
            assume_role_policy_changes.append(change)

        # All changes status must be not-applied at request creation
        change.status = Status.not_applied
        # Add ID for each change
        change.id = extended_request_uuid + str(incremental_change_id)
        incremental_change_id += 1

    # Make sure the requester is only ever 64 chars with domain
    if len(user) > 64:
        split_items: list = user.split("@")
        user: str = split_items[0][
            : (64 - (len(split_items[-1]) + 1))
        ] + "@" + split_items[-1]

    account_id = await get_resource_account(primary_principal_arn)
    arn_parsed = parse_arn(primary_principal_arn)

    # Only one assume role policy change allowed per request
    if len(assume_role_policy_changes) > 1:
        log_data["message"] = "One one assume role policy change supported per request."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    if (
        len(inline_policy_changes) > 0
        or len(managed_policy_changes) > 0
        or len(assume_role_policy_changes) > 0
    ):
        # for inline policies and managed policies, principal arn must be a role
        if arn_parsed["service"] != "iam" or arn_parsed["resource"] != "role":
            log_data[
                "message"
            ] = "ARN type not supported for inline/managed/assume role policy changes."
            log.error(log_data)
            raise InvalidRequestParameter(log_data["message"])
        role_name = arn_parsed["resource_path"].split("/")[-1]
        role = await get_role_details(account_id, role_name=role_name, extended=True)
        for inline_policy_change in inline_policy_changes:
            await validate_inline_policy_change(inline_policy_change, user, role)
        for managed_policy_change in managed_policy_changes:
            await validate_managed_policy_change(managed_policy_change, user, role)
        for assume_role_policy_change in assume_role_policy_changes:
            await validate_assume_role_policy_change(
                assume_role_policy_change, user, role
            )

    # TODO: validate resource policy logic when we are ready to apply that

    # If here, request is valid and can successfully be generated
    request_changes = ChangeModelArray(
        changes=inline_policy_changes
        + managed_policy_changes
        + resource_policy_changes
        + assume_role_policy_changes
    )
    extended_request = ExtendedRequestModel(
        id=extended_request_uuid,
        arn=primary_principal_arn,
        timestamp=int(time.time()),
        justification=request_creation.justification,
        requester_email=user,
        approvers=[],  # TODO: approvers logic (future feature)
        status="pending",
        changes=request_changes,
        requester_info=UserModel(
            email=user,
            extended_info=await auth.get_user_info(user),
            details_url=config.config_plugin().get_employee_info_url(user),
            photo_url=config.config_plugin().get_employee_photo_url(user),
        ),
        comments=[],
        cross_account=False,
    )
    await generate_resource_policies(extended_request, user)
    return extended_request


async def is_request_eligible_for_auto_approval(
    extended_request: ExtendedRequestModel, user: str
) -> bool:
    """
            Checks whether a request is eligible for auto-approval probes or not

            :param extended_request: ExtendedRequestModel
            :param user: username
            :return bool:
        """
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "arn": extended_request.arn,
        "request": extended_request.dict(),
        "message": "Checking whether request is eligible for auto-approval probes",
    }
    log.info(log_data)
    is_eligible = False

    # Currently the only allowances are: Inline policies
    for change in extended_request.changes.changes:
        # Exclude auto-generated resource policies from eligibility check
        if change.change_type == ChangeType.resource_policy and change.autogenerated:
            continue
        if change.change_type != ChangeType.inline_policy:
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
        "arn": extended_request.arn,
        "request": extended_request.dict(),
        "message": "Generating resource policies",
    }
    log.debug(log_data)

    role_account_id = await get_resource_account(extended_request.arn)
    arn_parsed = parse_arn(extended_request.arn)

    if arn_parsed["service"] != "iam" or arn_parsed["resource"] != "role":
        log_data[
            "message"
        ] = "ARN type not supported for generating resource policy changes."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    # TODO: do actual resource policy logic, rather than just the blank stub
    resource_policy = {"Version": "2012-10-17", "Statement": []}
    resource_policy_sha = sha256(json.dumps(resource_policy).encode()).hexdigest()
    primary_principal_resource_model = ResourceModel(
        arn=extended_request.arn,
        name=arn_parsed["resource_path"].split("/")[-1],
        account_id=role_account_id,
        resource_type=arn_parsed["service"],
    )

    auto_generated_resource_policy_changes = []

    # Create resource policy stubs for current resources that are used
    for policy_change in extended_request.changes.changes:
        if policy_change.change_type == ChangeType.inline_policy:
            for resource in policy_change.resources:
                resource_account_id = await get_resource_account(resource.arn)
                if resource_account_id != role_account_id:
                    # Cross account request
                    auto_generated_resource_policy_changes.append(
                        ResourcePolicyChangeModel(
                            arn=resource.arn,
                            policy=PolicyModel(
                                policy_document=resource_policy,
                                policy_sha256=resource_policy_sha,
                            ),
                            change_type=ChangeType.resource_policy,
                            principal_arn=extended_request.arn,
                            status=Status.not_applied,
                            sourceChangeID=policy_change.id,
                            id=str(uuid.uuid4()),
                            resources=[primary_principal_resource_model],
                            autogenerated=True,
                        )
                    )

    extended_request.changes.changes.extend(auto_generated_resource_policy_changes)
    if len(auto_generated_resource_policy_changes) > 0:
        extended_request.cross_account = True
    log_data["message"] = "Finished generating resource policies"
    log_data["request"] = extended_request.dict()
    log.debug(log_data)


async def validate_inline_policy_change(
    change: InlinePolicyChangeModel, user: str, role: ExtendedRoleModel
):
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "arn": change.principal_arn,
        "request": change.dict(),
        "message": "Validating inline policy change",
    }
    log.info(log_data)
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
            log_data["message"] = "Inline Policy with that name already exists."
            log.error(log_data)
            raise InvalidRequestParameter(log_data["message"])
        # Check if policy being updated is the same as existing policy.
        if (
            not change.new
            and change.policy.policy_document == existing_policy.get("PolicyDocument")
            and change.action == Action.attach
        ):
            log_data[
                "message"
            ] = "No changes were found between the updated and existing policy."
            log.error(log_data)
            raise InvalidRequestParameter(log_data["message"])
        if change.policy_name == existing_policy.get("PolicyName"):
            seen_policy_name = True

    # Trying to detach inline policy with name that isn't attached
    if change.action == Action.detach and not seen_policy_name:
        log_data["message"] = "Can't detach an inline policy that is not attached."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    if change.action == Action.attach and not seen_policy_name and not change.new:
        log_data[
            "message"
        ] = "Inline policy not seen but request claims change is not new"
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
        "request": change.dict(),
        "message": "Validating managed policy change",
    }
    log.info(log_data)
    if await invalid_characters_in_policy(change.policy_name):
        log_data["message"] = "Invalid characters were detected in the policy name."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])
    if change.action == Action1.attach:
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
    elif change.action == Action1.detach:
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


async def validate_assume_role_policy_change(
    change: AssumeRolePolicyChangeModel, user: str, role: ExtendedRoleModel
):
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "arn": change.principal_arn,
        "request": change.dict(),
        "message": "Validating assume role policy change",
    }
    log.info(log_data)
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
    extended_request: ExtendedRequestModel, response: RequestCreationResponse, user: str
) -> None:
    """
        Applies changes based on the changes array in the request, in a best effort manner to a role

        Caution: this method applies changes blindly... meaning it assumes before calling this method,
        you have validated the changes being made are authorized.

        :param extended_request: ExtendedRequestModel
        :param user: Str - requester's email address
        :param response: RequestCreationResponse
    """

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "request": extended_request.dict(),
        "message": "Applying request changes",
    }
    log.info(log_data)

    arn_parsed = parse_arn(extended_request.arn)

    # Principal ARN must be a role for this function
    if arn_parsed["service"] != "iam" or arn_parsed["resource"] != "role":
        log_data[
            "message"
        ] = "ARN type not supported for inline/managed/assume role policy changes."
        log.error(log_data)
        response.errors += 1
        response.action_results.append(
            ActionResult(status="error", message=log_data["message"],)
        )
        return

    role_name = arn_parsed["resource_path"].split("/")[-1]
    account_id = await get_resource_account(extended_request.arn)
    iam_client = await sync_to_async(boto3_cached_conn)(
        "iam",
        service_type="client",
        account_number=account_id,
        region=config.region,
        assume_role=config.get("policies.role_name"),
        session_name="role-updater-v2-" + user,
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
        if change.change_type == ChangeType.inline_policy:
            if change.action == Action.attach:
                try:
                    await sync_to_async(iam_client.put_role_policy)(
                        RoleName=role_name,
                        PolicyName=change.policy_name,
                        PolicyDocument=json.dumps(change.policy.policy_document),
                    )
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=f"Successfully applied inline policy {change.policy_name} to role: {role_name}",
                        )
                    )
                    change.status = Status.applied
                except Exception as e:
                    log_data["message"] = "Exception occurred applying inline policy"
                    log_data["error"] = str(e)
                    log.error(log_data, exc_info=True)
                    config.sentry.captureException()
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=f"Error occurred applying inline policy {change.policy_name} to role: {role_name}: "
                            + str(e),
                        )
                    )
            elif change.action == Action.detach:
                try:
                    await sync_to_async(iam_client.delete_role_policy)(
                        RoleName=role_name, PolicyName=change.policy_name
                    )
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=f"Successfully deleted inline policy {change.policy_name} from role: {role_name}",
                        )
                    )
                    change.status = Status.applied
                except Exception as e:
                    log_data["message"] = "Exception occurred deleting inline policy"
                    log_data["error"] = str(e)
                    log.error(log_data, exc_info=True)
                    config.sentry.captureException()
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=f"Error occurred deleting inline policy {change.policy_name} from role: {role_name} "
                            + str(e),
                        )
                    )
        elif change.change_type == ChangeType.managed_policy:
            if change.action == Action1.attach:
                try:
                    await sync_to_async(iam_client.attach_role_policy)(
                        RoleName=role_name, PolicyArn=change.arn
                    )
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=f"Successfully attached managed policy {change.arn} to role: {role_name}",
                        )
                    )
                    change.status = Status.applied
                except Exception as e:
                    log_data["message"] = "Exception occurred attaching managed policy"
                    log_data["error"] = str(e)
                    log.error(log_data, exc_info=True)
                    config.sentry.captureException()
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=f"Error occurred attaching managed policy {change.arn} to role: {role_name}: "
                            + str(e),
                        )
                    )
            elif change.action == Action1.detach:
                try:
                    await sync_to_async(iam_client.detach_role_policy)(
                        RoleName=role_name, PolicyArn=change.arn
                    )
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=f"Successfully detached managed policy {change.arn} from role: {role_name}",
                        )
                    )
                    change.status = Status.applied
                except Exception as e:
                    log_data["message"] = "Exception occurred detaching managed policy"
                    log_data["error"] = str(e)
                    log.error(log_data, exc_info=True)
                    config.sentry.captureException()
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=f"Error occurred detaching managed policy {change.arn} from role: {role_name}: "
                            + str(e),
                        )
                    )
        elif change.change_type == ChangeType.assume_role_policy:
            try:
                await sync_to_async(iam_client.update_assume_role_policy)(
                    RoleName=role_name,
                    PolicyDocument=json.dumps(change.policy.policy_document),
                )
                response.action_results.append(
                    ActionResult(
                        status="success",
                        message=f"Successfully updated assume role policy policy for role: {role_name}",
                    )
                )
                change.status = Status.applied
            except Exception as e:
                log_data[
                    "message"
                ] = "Exception occurred updating assume role policy policy"
                log_data["error"] = str(e)
                log.error(log_data, exc_info=True)
                config.sentry.captureException()
                response.errors += 1
                response.action_results.append(
                    ActionResult(
                        status="error",
                        message=f"Error occurred updating assume role policy for role: {role_name}: "
                        + str(e),
                    )
                )
        else:
            # unsupported type for auto-application
            response.action_results.append(
                ActionResult(
                    status="error",
                    message=f"Error occurred applying: Change type {change.change_type.value} is not supported",
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


async def populate_old_policies(extended_request: ExtendedRequestModel, user: str):
    """
        Populates the old policies for each inline policy.
        Note: Currently only applicable when the principal ARN is a role and for old inline_policies, assume role policy

        :param extended_request: ExtendedRequestModel
        :param user: username
        :return:
    """

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "arn": extended_request.arn,
        "request": extended_request.dict(),
        "message": "Populating old policies",
    }
    log.debug(log_data)

    role_account_id = await get_resource_account(extended_request.arn)
    arn_parsed = parse_arn(extended_request.arn)

    if arn_parsed["service"] != "iam" or arn_parsed["resource"] != "role":
        log_data[
            "message"
        ] = "ARN type not supported for generating resource policy changes."
        log.error(log_data)
        return

    role_name = arn_parsed["resource_path"].split("/")[-1]
    role = await get_role_details(role_account_id, role_name=role_name, extended=True)

    for change in extended_request.changes.changes:
        if change.change_type == ChangeType.assume_role_policy:
            change.old_policy = PolicyModel(
                policy_sha256=sha256(
                    json.dumps(role.assume_role_policy_document).encode()
                ).hexdigest(),
                policy_document=role.assume_role_policy_document,
            )
        elif change.change_type == ChangeType.inline_policy and not change.new:
            for existing_policy in role.inline_policies:
                if change.policy_name == existing_policy.get("PolicyName"):
                    change.old_policy = PolicyModel(
                        policy_sha256=sha256(
                            json.dumps(existing_policy.get("PolicyDocument")).encode()
                        ).hexdigest(),
                        policy_document=existing_policy.get("PolicyDocument"),
                    )
                    break

    log_data["message"] = "Done populating old policies"
    log_data["request"] = extended_request.dict()
    log.debug(log_data)


async def populate_cross_account_resource_policies(
    extended_request: ExtendedRequestModel, user: str
) -> bool:
    """
        Populates the cross-account resource policies for supported resources for each inline policy.
        :param extended_request: ExtendedRequestModel
        :param user: username
        :return: changed: whether the resource policies have changed or not
    """

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "arn": extended_request.arn,
        "request": extended_request.dict(),
        "message": "Populating cross-account resource policies",
    }
    log.debug(log_data)

    supported_resource_policies = config.get(
        "policies.supported_resource_types_for_policy_application", []
    )
    resource_policies_changed = False
    for change in extended_request.changes.changes:
        if change.change_type == ChangeType.resource_policy and change.autogenerated:
            # autogenerated resource policy change
            resource_arn_parsed = parse_arn(change.arn)
            resource_type = resource_arn_parsed["service"]
            resource_name = resource_arn_parsed["resource"]
            resource_region = resource_arn_parsed["region"]
            resource_account = resource_arn_parsed["account"]
            if not resource_account:
                resource_account = await get_resource_account(change.arn)
            if resource_type in supported_resource_policies:
                change.supported = True
            else:
                change.supported = False
            old_policy = await get_resource_policy(
                account=resource_account,
                resource_type=resource_type,
                name=resource_name,
                region=resource_region,
            )
            old_policy_sha256 = sha256(json.dumps(old_policy).encode()).hexdigest()
            if (
                change.old_policy
                and old_policy_sha256 == change.old_policy.policy_sha256
            ):
                # Old policy hasn't changed since last refresh of page, no need to generate resource policy again
                continue
            # Otherwise it has changed, regenerate the resource policies
            resource_policies_changed = True
            change.old_policy = PolicyModel(
                policy_sha256=old_policy_sha256, policy_document=old_policy,
            )
            # Have to grab the actions from the source inline change
            actions = []
            resource_arns = []
            for source_change in extended_request.changes.changes:
                # Find the specific inline policy associated with this change
                if (
                    source_change.change_type == ChangeType.inline_policy
                    and source_change.id == change.sourceChangeID
                ):
                    for statement in source_change.policy.policy_document.get(
                        "Statement", []
                    ):
                        # Find the specific statement within the inline policy associated with this resource
                        if change.arn in statement.get("Resource"):
                            actions.extend(statement.get("Action", []))
                            resource_arns.extend(statement.get("Resource", []))
            new_policy = await update_resource_policy(
                existing=old_policy,
                principal_arn=extended_request.arn,
                resource_arns=list(set(resource_arns)),
                actions=actions,
            )
            new_policy_sha256 = sha256(json.dumps(new_policy).encode()).hexdigest()
            change.policy = PolicyModel(
                policy_sha256=new_policy_sha256, policy_document=new_policy,
            )

    log_data["message"] = "Done populating cross account resource policies"
    log_data["request"] = extended_request.dict()
    log_data["resource_policies_changed"] = resource_policies_changed
    log.debug(log_data)
    return resource_policies_changed

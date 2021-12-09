import time
from hashlib import sha256
from typing import Dict, List, Optional

import ujson as json
from policy_sentry.querying.actions import get_actions_with_access_level

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    InvalidRequestParameter,
    MissingConfigurationValue,
)
from consoleme.lib.account_indexers import get_account_id_to_name_mapping
from consoleme.lib.aws import minimize_iam_policy_statements
from consoleme.lib.defaults import SELF_SERVICE_IAM_DEFAULTS
from consoleme.lib.generic import generate_random_string, iterate_and_format_dict
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.models import (
    ChangeGeneratorModel,
    ChangeGeneratorModelArray,
    ChangeModelArray,
    CrudChangeGeneratorModel,
    InlinePolicyChangeModel,
    PolicyModel,
    ResourceModel,
    Status,
)

group_mapping = get_plugin_by_name(
    config.get("plugins.group_mapping", "default_group_mapping")
)()
ALL_ACCOUNTS = None

self_service_iam_config: dict = config.get(
    "self_service_iam", SELF_SERVICE_IAM_DEFAULTS
)


async def _generate_policy_statement(
    actions: List, resources: List, effect: str, condition: Dict
) -> Dict:
    """
    Generates an IAM policy resource given actions, effects, resources, and conditions
    :param actions: a List of actions
    :param resources: a List of AWS resource ARNs or wildcards
    :param effect: an Effect (Allow|Deny)
    :return:
    """

    policy_statement = {
        "Action": list(set(actions)),
        "Effect": effect,
        "Resource": list(set(resources)),
    }
    if condition:
        policy_statement["Condition"] = condition
    return policy_statement


async def _generate_policy_sid(user: str) -> str:
    """
    Generate a unique SID identifying the user and time of the change request.

    :param user: User's e-mail address
    :return: policy SID string
    """
    user_stripped = user.split("@")[0]
    # Strip out any special characters from username
    user_stripped = "".join(e for e in user_stripped if e.isalnum())
    random_string = await generate_random_string()
    return f"cm{user_stripped}{int(time.time())}{random_string}"


async def generate_policy_name(
    policy_name: str, user: str, expiration_date: Optional[int] = None
) -> str:
    """
    Generate a unique policy name identifying the user and time of the change request.

    :param policy_name: A predefined policy name that will override the generated one, if it exists
    :param user: User's e-mail address
    :return: policy name string
    """
    temp_policy_prefix = config.get("policies.temp_policy_prefix", "cm_delete-on")
    if policy_name:
        return policy_name
    user_stripped = user.split("@")[0]
    random_string = await generate_random_string()
    if expiration_date:
        return (
            f"{temp_policy_prefix}_{expiration_date}_{user_stripped}_{int(time.time())}"
        )
    return f"cm_{user_stripped}_{int(time.time())}_{random_string}"


async def _generate_inline_policy_model_from_statements(
    statements: List[Dict],
) -> PolicyModel:
    """
    given a list of policy statements, generate a policy
    :param statements: List[Dict] - list of policy statements
    :return:
    """
    policy_document = {"Version": "2012-10-17", "Statement": statements}
    policy_string = json.dumps(policy_document)
    policy_input = {
        "policy_document": policy_document,
        "policy_sha256": sha256(policy_string.encode()).hexdigest(),
    }
    return PolicyModel(**policy_input)


async def _generate_inline_policy_change_model(
    principal: str,
    resources: List[ResourceModel],
    statements: List[Dict],
    user: str,
    is_new: bool = True,
    policy_name: Optional[str] = None,
) -> InlinePolicyChangeModel:
    """
    Generates an inline policy change model.

    :param principal: principal associated with the InlinePolicyChangeModel
    :param resources: Resource ARNs (or wildcards) of the resources associated with the InlinePolicyChangeModel
    :param statements: A list of AWS IAM policy statement dictionaries
    :param user: User e-mail address
    :param is_new: Boolean representing if we're creating a new policy or updating an existing policy
    :param policy_name: Optional policy name. If not provided, one will be generated
    :return: InlinePolicyChangeModel
    """
    policy_name = await generate_policy_name(policy_name, user)
    policy_document = await _generate_inline_policy_model_from_statements(statements)
    change_details = {
        "change_type": "inline_policy",
        "principal": principal,
        "resources": resources,
        "policy_name": policy_name,
        "new": is_new,
        "policy": policy_document,
        "status": Status.not_applied,
    }
    return InlinePolicyChangeModel(**change_details)


async def _get_policy_sentry_access_level_actions(
    service: str, access_levels: List[str]
) -> List[str]:
    """Use policy_sentry to get actions corresponding to AWS service and access_levels.
    TODO(psanders): Move this to a more sensible module

    :param resource_arn: Resource ARN (or wildcards) of the resource associated with the change
    :param access_levels: a list of CRUD operations to generate IAM policy statmeents from
    :return: actions: A list of IAM policy actions
    """
    actions: List[str] = []
    for level in access_levels:
        actions += get_actions_with_access_level(service, level)
    return actions


async def _get_actions_from_groups(
    action_groups: List[str], permissions_map: Dict[List, Dict[str, List[str]]]
) -> List[str]:
    """Get actions based on "groups" defined in permissions_map
    TODO(psanders): Move this to a more sensible module

    :param action_groups: A list of requested CRUD operations to convert into IAM actions
    :param permissions_map: A mapping of actions associated with the resource type, usually from configuration
    :return: actions: A list of IAM policy actions
    """
    actions: List[str] = []
    for ag in action_groups:
        for pm in permissions_map:
            if pm["name"] == ag:
                actions += pm.get("permissions", [])
    if not actions:
        raise InvalidRequestParameter(
            f"One or more of the passed actions is invalid for the generator type: {action_groups}"
        )
    return actions


async def _generate_s3_inline_policy_statement_from_mapping(
    generator: ChangeGeneratorModel,
) -> Dict:
    """
    Generates an S3 inline policy statement from a ChangeGeneratorModel. S3 is an edge case, thus it gets a
    unique function for this purpose. We need to consider the resource ARN and prefix.

    :param generator: ChangeGeneratorModel
    :return: policy_statement: A dictionary representing an inline policy statement.
    """
    permissions_map = (
        self_service_iam_config.get("permissions_map", {})
        .get("s3", {})
        .get("action_map")
    )
    if not permissions_map:
        raise MissingConfigurationValue(
            "Unable to find applicable action map configuration."
        )
    action_group_actions: List[str] = []
    resource_arns = []
    effect = generator.effect
    condition = generator.condition

    if isinstance(generator.resource_arn, str):
        generator.resource_arn = [generator.resource_arn]
    # Handle the bucket ARNs
    for arn in generator.resource_arn:
        if not arn.startswith("arn:aws:s3:::"):
            arn = f"arn:aws:s3:::{arn}"
        resource_arns.append(arn)

        # Make sure prefix starts with "/"
        if not generator.bucket_prefix.startswith("/"):
            generator.bucket_prefix = f"/{generator.bucket_prefix}"

        resource_arns.append(f"{arn}{generator.bucket_prefix}")

    for action in generator.action_groups:
        action_group_actions.append(action)
    actions = await _get_actions_from_groups(action_group_actions, permissions_map)
    if generator.extra_actions:
        actions.extend(generator.extra_actions)
    return await _generate_policy_statement(actions, resource_arns, effect, condition)


async def _generate_condition_with_substitutions(generator: ChangeGeneratorModel):
    """
    Generates a condition with substitutions if they are needed.

    :param generator:
    :return:
    """
    condition: Optional[Dict] = generator.condition
    if isinstance(condition, dict):
        condition = await iterate_and_format_dict(condition, generator.dict())
    return condition


async def _generate_inline_policy_statement_from_mapping(
    generator: ChangeGeneratorModel,
) -> Dict:
    """
    Generates an inline policy statement given a ChangeGeneratorModel from a action mapping stored in configuration.

    :param generator: ChangeGeneratorModel
    :return: policy_statement: A dictionary representing an inline policy statement.
    """
    generator_type = generator.generator_type
    if not isinstance(generator_type, str):
        generator_type = generator.generator_type.value
    permissions_map = (
        self_service_iam_config.get("permissions_map", {})
        .get(generator_type, {})
        .get("action_map")
    )
    if not permissions_map:
        raise MissingConfigurationValue(
            f"Unable to find applicable action map configuration for {generator_type}."
        )

    action_group_actions: List[str] = []
    if isinstance(generator.resource_arn, str):
        generator.resource_arn = [generator.resource_arn]
    resource_arns = generator.resource_arn
    effect = generator.effect

    for action in generator.action_groups:
        # TODO: Seems like a datamodel bug when we don't have a enum defined for an array type, but I need to access
        # this as a string sometimes
        if isinstance(action, str):
            action_group_actions.append(action)
        else:
            action_group_actions.append(action)
    actions = await _get_actions_from_groups(action_group_actions, permissions_map)
    if generator.extra_actions:
        actions.extend(generator.extra_actions)
    condition: Optional[Dict] = await _generate_condition_with_substitutions(generator)
    return await _generate_policy_statement(actions, resource_arns, effect, condition)


async def _generate_inline_policy_statement_from_policy_sentry(
    generator: CrudChangeGeneratorModel,
) -> Dict:
    """
    Generates an inline policy statement given a ChangeGeneratorModel from a action mapping provided by policy
    sentry.

    :param generator: ChangeGeneratorModel
    :return: policy_statement: A dictionary representing an inline policy statement.
    """
    permissions_map = (
        self_service_iam_config.get("permissions_map", {})
        .get("crud_lookup", {})
        .get("action_map")
    )
    if not permissions_map:
        raise MissingConfigurationValue(
            "Unable to find applicable action map configuration."
        )
    access_level_actions: List[str] = []
    for access in generator.action_groups:
        for pm in permissions_map:
            if pm["name"] == access:
                access_level_actions += pm.get("permissions")
    actions = await _get_policy_sentry_access_level_actions(
        generator.service_name, access_level_actions
    )
    if generator.extra_actions:
        actions.extend(generator.extra_actions)
    if isinstance(generator.resource_arn, str):
        generator.resource_arn = [generator.resource_arn]
    return await _generate_policy_statement(
        actions, generator.resource_arn, generator.effect, generator.condition
    )


async def _generate_inline_iam_policy_statement_from_change_generator(
    change: ChangeGeneratorModel,
) -> Dict:
    """
    Generates an inline policy statement from a ChangeGeneratorModel.
    :param change: ChangeGeneratorModel
    :return: policy_statement: A dictionary representing an inline policy statement.
    """
    generator_type = change.generator_type
    if not isinstance(generator_type, str):
        generator_type = change.generator_type.value
    if generator_type == "s3":
        policy = await _generate_s3_inline_policy_statement_from_mapping(change)
    elif generator_type == "crud_lookup":
        policy = await _generate_inline_policy_statement_from_policy_sentry(change)
    else:
        policy = await _generate_inline_policy_statement_from_mapping(change)

    # Honeybee supports restricting policies to certain accounts.
    if change.include_accounts:
        policy["IncludeAccounts"] = change.include_accounts
    if change.exclude_accounts:
        policy["ExcludeAccounts"] = change.exclude_accounts
    return policy


async def _attach_sids_to_policy_statements(
    inline_iam_policy_statements: List[Dict], user: str
) -> List[Dict]:
    """
    Generates and attaches Sids to each policy statement if the statement does not already have a Sid.

    :param inline_iam_policy_statements: A list of IAM policy statement dictionaries
    :param user: The acting user's email address
    :return: A list of IAM policy statement dictionaries with Sid entries for each
    """
    for statement in inline_iam_policy_statements:
        if not statement.get("Sid"):
            statement["Sid"] = await _generate_policy_sid(user)
    return inline_iam_policy_statements


async def _generate_resource_model_from_arn(arn: str) -> Optional[ResourceModel]:
    """
    Generates a ResourceModel from a Resource ARN

    :param arn: AWS resource identifier
    :return: ResourceModel
    """
    try:
        account_id = arn.split(":")[4]
        resource_type = arn.split(":")[2]
        region = arn.split(":")[3]
        name = arn.split(":")[5].split("/")[-1]
        if not region:
            region = "global"
        global ALL_ACCOUNTS
        if not ALL_ACCOUNTS:
            ALL_ACCOUNTS = await get_account_id_to_name_mapping()
        account_name = ALL_ACCOUNTS.get(account_id, "")

        return ResourceModel(
            arn=arn,
            name=name,
            account_id=account_id,
            account_name=account_name,
            resource_type=resource_type,
            region=region,
        )
    except IndexError:
        # Resource is not parsable or a wildcard.
        return


async def generate_change_model_array(
    changes: ChangeGeneratorModelArray,
) -> ChangeModelArray:
    """
    Compiles a ChangeModelArray which includes all of the AWS policies required to satisfy the
    ChangeGeneratorModelArray request.

    :param changes: ChangeGeneratorModelArray
    :return: ChangeModelArray
    """

    change_models = []
    inline_iam_policy_statements: List[Dict] = []
    primary_principal = None
    primary_user = None
    resources = []

    for change in changes.changes:
        # Enforce a maximum of one user per ChangeGeneratorModelArray (aka Policy Request)
        if not primary_user:
            primary_user = change.user
        if primary_user != change.user:
            raise InvalidRequestParameter(
                "All changes associated with request must be associated with the same user."
            )

        # Enforce a maximum of one principal ARN per ChangeGeneratorModelArray (aka Policy Request)
        if not primary_principal:
            primary_principal = change.principal
        if primary_principal != change.principal:
            raise InvalidRequestParameter(
                "We only support making changes to a single principal ARN per request."
            )

        if change.generator_type == "custom_iam":
            inline_policies = change.policy["Statement"]
            if isinstance(inline_policies, dict):
                inline_policies = [inline_policies]
        else:
            # Generate inline policy for the change, if applicable
            inline_policies = [
                await _generate_inline_iam_policy_statement_from_change_generator(
                    change
                )
            ]
        for inline_policy in inline_policies:
            # Inline policies must have Action|NotAction, Resource|NotResource, and an Effect
            if inline_policy and (
                (not inline_policy.get("Action") and not inline_policy.get("NotAction"))
                or (
                    not inline_policy.get("Resource")
                    and not inline_policy.get("NotResource")
                )
                or not inline_policy.get("Effect")
            ):
                raise InvalidRequestParameter(
                    f"Generated inline policy is invalid. Double-check request parameter: {inline_policy}"
                )
            if inline_policy and change.resource_arn:
                # TODO(ccastrapel): Add more details to the ResourceModel when we determine we can use it for something.
                if isinstance(change.resource_arn, str):
                    change.resource_arn = [change.resource_arn]
                for arn in change.resource_arn:
                    resource_model = await _generate_resource_model_from_arn(arn)
                    # If the resource arn is actually a wildcard, we might not have a valid resource model
                    if resource_model:
                        resources.append(resource_model)
            if inline_policy:
                inline_iam_policy_statements.append(inline_policy)

        # TODO(ccastrapel): V2: Generate resource policies for the change, if applicable

    # Minimize the policy statements to remove redundancy
    inline_iam_policy_statements = await minimize_iam_policy_statements(
        inline_iam_policy_statements
    )
    # Attach Sids to each of the statements that will help with identifying who made the request and when.
    inline_iam_policy_statements = await _attach_sids_to_policy_statements(
        inline_iam_policy_statements, primary_user
    )
    # TODO(ccastrapel): Check if the inline policy statements would be auto-approved and supply that context
    inline_iam_policy_change_model = await _generate_inline_policy_change_model(
        primary_principal, resources, inline_iam_policy_statements, primary_user
    )
    change_models.append(inline_iam_policy_change_model)
    return ChangeModelArray.parse_obj({"changes": change_models})

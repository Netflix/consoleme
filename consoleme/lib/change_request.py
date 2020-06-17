import time
from hashlib import sha256
from typing import Dict, List, Optional

import ujson as json
from deepdiff import DeepDiff
from policy_sentry.querying.actions import get_actions_with_access_level
from policy_sentry.util.arns import get_service_from_arn

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    InvalidRequestParameter,
    MissingConfigurationValue,
)
from consoleme.lib.generic import generate_random_string
from consoleme.models import (
    ChangeGeneratorModel,
    ChangeGeneratorModelArray,
    ChangeModel,
    ChangeModelArray,
    ChangeType,
    GeneratorType,
    GenericChangeGeneratorModel,
    InlinePolicyChangeModel,
    PolicyModel,
    ResourcePolicyChangeModel,
)


async def get_resource_policy_changes(
    principal_arn: str, changes: List[ChangeModel]
) -> List[ResourcePolicyChangeModel]:
    # TODO
    pass


async def _generate_policy_statement(
    actions: List, resources: List, effect: str, condition: Dict
) -> Dict:
    """
    Generates an IAM policy resource given actions, effects, resources, and conditions
    :param actions:
    :param resources:
    :param effect:
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


async def _generate_policy_sid(user):
    # "AllowedPatternRegex": "^[a-zA-Z0-9+=,.@\\-_]+$",
    user_stripped = user.split("@")[0]
    random_string = await generate_random_string()
    return f"cm{user_stripped}{int(time.time())}{random_string}"


async def _generate_policy_name(policy_name, user):
    # "AllowedPatternRegex": "^[a-zA-Z0-9+=,.@\\-_]+$",
    if policy_name:
        return policy_name
    user_stripped = user.split("@")[0]
    random_string = await generate_random_string()
    return f"cm_{user_stripped}_{int(time.time())}_{random_string}"


async def _generate_inline_policy_model_from_statements(
    statements: List
) -> PolicyModel:
    policy_string = json.dumps({"Version": "2012-10-17", "Statement": [statements]})
    policy_input = {
        "policy_document": policy_string,
        "policy_sha256": sha256(policy_string.encode()).hexdigest(),
    }
    return PolicyModel(**policy_input)


async def _generate_change(
    principal_arn: str,
    resource_arns: List[str],
    statements: List[Dict],
    user: str,
    is_new: bool = True,
    policy_name: Optional[str] = None,
):
    policy_name = await _generate_policy_name(policy_name, user)
    policy_document = await _generate_inline_policy_model_from_statements(statements)
    change_details = {
        "change_type": ChangeType.inline_policy,
        "principal_arn": principal_arn,
        "resource_arns": resource_arns,
        "policy_name": policy_name,
        "new": is_new,
        "policy": policy_document,
    }
    return InlinePolicyChangeModel(**change_details)


async def _get_access_level_actions_for_resource(
    resource_arn: str, access_levels: List[str]
) -> List[str]:
    """Use policy_sentry to get actions corresponding to AWS service and access_levels.
    TODO(psanders): Move this to a more sensible module

    :param resource_arn:
    :param access_levels:
    :return:
    """
    service = get_service_from_arn(resource_arn)
    actions: List[str] = []
    for level in access_levels:
        actions += get_actions_with_access_level(service, level)
    return actions


async def _get_actions_from_groups(
    action_groups: List[str], action_map: Dict[str, List[str]]
) -> List[str]:
    """Get actions based on "groups" defined in action_map
    TODO(psanders): Move this to a more sensible module

    :param action_groups:
    :param action_map:
    :return:
    """
    actions: List[str] = []
    for ag in action_groups:
        actions += action_map.get(ag, {}).get("permissions", [])
    if not actions:
        raise InvalidRequestParameter(
            f"One or more of the passed actions is invalid for the generator type: {action_groups}"
        )
    return actions


async def _generate_s3_inline_policy_statement(generator: ChangeGeneratorModel) -> Dict:
    action_map = config.get("self_service_iam.change_types.s3.actions")
    if not action_map:
        raise MissingConfigurationValue(
            "Unable to find applicable action map configuration."
        )
    action_group_actions: List[str] = []
    resource_arns = []
    effect = generator.effect
    condition = generator.condition

    # Handle the bucket ARN
    if not generator.resource_arn.startswith("arn:aws:s3:::"):
        generator.resource_arn = f"arn:aws:s3:::{generator.resource_arn}"
    resource_arns.append(generator.resource_arn)

    # Handle the prefix ARN
    if generator.bucket_prefix:
        # Make sure prefix starts with "/"
        if not generator.bucket_prefix.startswith("/"):
            generator.bucket_prefix = f"/{generator.bucket_prefix}"
    else:
        # Default to allowing the entire bucket
        generator.bucket_prefix = "/*"
    resource_arns.append(f"{generator.resource_arn}{generator.bucket_prefix}")

    for action in generator.action_groups:
        action_group_actions.append(action.value)
    actions = await _get_actions_from_groups(action_group_actions, action_map)
    return await _generate_policy_statement(actions, resource_arns, effect, condition)


# TODO(ccastrapel): This is confusing since we have a generic model already
async def _generate_general_inline_policy_statement(
    generator: ChangeGeneratorModel
) -> Dict:
    action_map = config.get(
        f"self_service_iam.change_types.{generator.generator_type.value}.actions"
    )
    if not action_map:
        raise MissingConfigurationValue(
            f"Unable to find applicable action map configuration for {generator.generator_type}."
        )

    action_group_actions: List[str] = []
    resource_arns = [generator.resource_arn]
    effect = generator.effect
    condition = generator.condition

    for action in generator.action_groups:
        action_group_actions.append(action.value)
    actions = await _get_actions_from_groups(action_group_actions, action_map)
    return await _generate_policy_statement(actions, resource_arns, effect, condition)


async def _generate_generic_inline_policy_statement(
    generator: GenericChangeGeneratorModel,
) -> Dict:
    action_map = config.get("self_service_iam.change_types.generic.generic_actions")
    if not action_map:
        raise MissingConfigurationValue(
            "Unable to find applicable action map configuration."
        )
    access_level_actions: List[str] = []
    for access in generator.access_level:
        access_level_actions.append(action_map.get(access.value))
    actions = await _get_access_level_actions_for_resource(
        generator.resource_arn, access_level_actions
    )
    return await _generate_policy_statement(
        actions, [generator.resource_arn], generator.effect, generator.condition
    )


async def _generate_inline_iam_policy_statement_from_change_generator(
    change: ChangeGeneratorModel
) -> Dict:
    """
    Generates an inline policy statement from a ChangeGeneratorModel.
    :param change:
    :return:
    """
    if change.generator_type == GeneratorType.s3:
        return await _generate_s3_inline_policy_statement(change)
    if change.generator_type == GeneratorType.generic:
        return await _generate_generic_inline_policy_statement(change)
    return await _generate_general_inline_policy_statement(change)
    # TODO: Custom policy handler
    pass


async def _minimize_iam_policy_statements(inline_iam_policy_statements: List) -> List:
    """
    Minimizes a list of inline IAM policy statements.

    1. Policies that are identical except for the resources will have the resources merged into a single statement
    with the same actions, effects, conditions, etc.

    2. Policies that have an identical resource, but different actions, will be combined if the rest of the policy
    is identical.
    """
    exclude_ids = []
    minimized_policies = []

    for i in range(len(inline_iam_policy_statements)):
        inline_iam_policy_statement = inline_iam_policy_statements[i]
        for j in range(i + 1, len(inline_iam_policy_statements)):
            inline_iam_policy_statement_to_compare = inline_iam_policy_statements[j]

            # Check to see if policy statements are identical except for Resources,
            # then except for Actions, and merge if possible
            for element in ["Resource", "Action"]:
                diff = DeepDiff(
                    inline_iam_policy_statement,
                    inline_iam_policy_statement_to_compare,
                    ignore_order=True,
                    exclude_paths=[f"root['{element}']"],
                )
                if not diff:
                    exclude_ids.append(j)
                    # Policy can be minimized
                    inline_iam_policy_statement[element] = sorted(
                        list(
                            set(
                                inline_iam_policy_statement[element]
                                + inline_iam_policy_statement_to_compare[element]
                            )
                        )
                    )
                    break

    for i in range(len(inline_iam_policy_statements)):
        if i not in exclude_ids:
            minimized_policies.append(inline_iam_policy_statements[i])
    # TODO(cccastrapel): Intelligently combine actions and/or resources if they include wildcards
    return minimized_policies


async def _attach_sids_to_policy_statements(
    inline_iam_policy_statements: List, user: str
) -> List:
    for statement in inline_iam_policy_statements:
        statement["Sid"] = await _generate_policy_sid(user)
    return inline_iam_policy_statements


async def generate_change_model_array(
    changes: ChangeGeneratorModelArray
) -> ChangeModelArray:
    """
    Generates ChangeModelArray of all changes required to satisfy ChangeGeneratorModelArray

    :param changes:
    :return:
    """

    change_models = []
    inline_iam_policy_statements: List[Dict] = []
    primary_principal_arn = None
    primary_user = None
    resource_arns = []

    for change in changes.changes:
        # Enforce a maximum of one user per ChangeGeneratorModelArray (aka Policy Request)
        if not primary_user:
            primary_user = change.user
        if primary_user != change.user:
            raise InvalidRequestParameter(
                "All changes associated with request must be associated with the same user."
            )

        # Enforce a maximum of one principal ARN per ChangeGeneratorModelArray (aka Policy Request)
        if not primary_principal_arn:
            primary_principal_arn = change.principal_arn
        if primary_principal_arn != change.principal_arn:
            raise InvalidRequestParameter(
                "We only support making changes to a single principal ARN per request."
            )

        # Generate inline policy for the change, if applicable
        inline_policy = await _generate_inline_iam_policy_statement_from_change_generator(
            change
        )
        if inline_policy and (
            not inline_policy.get("Action")
            or not inline_policy.get("Effect")
            or not inline_policy.get("Resource")
        ):
            raise InvalidRequestParameter(
                f"Generated inline policy is invalid. Double-check request parameter: {inline_policy}"
            )
        if inline_policy:
            resource_arns.append(change.resource_arn)
            inline_iam_policy_statements.append(inline_policy)

        # TODO(ccastrapel): V2: Generate resource policies for the change, if applicable

    # Minimize the policy statements to remove redundancy
    inline_iam_policy_statements = await _minimize_iam_policy_statements(
        inline_iam_policy_statements
    )
    # Attach Sids to each of the statements that will help with identifying who made the request and when.
    inline_iam_policy_statements = await _attach_sids_to_policy_statements(
        inline_iam_policy_statements, primary_user
    )
    # TODO(ccastrapel): Check if the inline policy statements would be auto-approved
    inline_iam_policy_change_model = await _generate_change(
        primary_principal_arn, resource_arns, inline_iam_policy_statements, primary_user
    )
    change_models.append(inline_iam_policy_change_model)
    return ChangeModelArray.parse_obj(change_models)

    # for change in changes.changes:
    #     if change.generator_type == GeneratorType.generic:
    #         generic_cgm = GenericChangeGeneratorModel.parse_obj(change)
    #         change_objects.append(generic_cgm)
    #         #change_model = await generate_generic_change(generic_cgm)
    #     elif change.generator_type == GeneratorType.s3:
    #         s3_cgm = S3ChangeGeneratorModel.parse_obj(change)
    #         change_objects.append(s3_cgm)
    #         #change_model = await generate_s3_change(s3_cgm)
    #     elif change.generator_type == GeneratorType.sns:
    #         sns_cgm = SNSChangeGeneratorModel.parse_obj(change)
    #         change_objects.append(sns_cgm)
    #         #change_model = await generate_sns_change(sns_cgm)
    #     elif change.generator_type == GeneratorType.sqs:
    #         sqs_cgm = SQSChangeGeneratorModel.parse_obj(change)
    #         change_objects.append(sqs_cgm)
    #         #change_model = await generate_sqs_change(sqs_cgm)
    #     else:
    #         # should never hit this case, but having this in case future code changes cause this
    #         # or we forgot to add stuff here when more generator types are added
    #         raise NotImplementedError
    #     change_models.append(change_model)
    # return ChangeModelArray.parse_obj(change_models)

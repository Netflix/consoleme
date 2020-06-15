from hashlib import sha256
from typing import Dict, List

import ujson as json
from policy_sentry.querying.actions import get_actions_with_access_level
from policy_sentry.util.arns import get_service_from_arn

from consoleme.config import config
from consoleme.exceptions.exceptions import MissingConfigurationValue
from consoleme.models import (
    ChangeModel,
    ChangeType,
    GenericChangeGeneratorModel,
    InlinePolicyChangeModel,
    PolicyModel,
    ResourcePolicyChangeModel,
    S3ChangeGeneratorModel,
    SNSChangeGeneratorModel,
    SQSChangeGeneratorModel,
)


def get_resource_policy_changes(
    principal_arn: str, changes: List[ChangeModel]
) -> List[ResourcePolicyChangeModel]:
    pass


async def _generate_iam_policy(
    resources: List[str], actions: List[str], effect: str = "Allow", sid: str = ""
) -> PolicyModel:
    # Deduplicate actions, then sort them to make this function deterministic
    deduped_actions = list(set(actions))
    deduped_actions.sort()
    policy_string = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": sid,
                    "Action": deduped_actions,
                    "Effect": effect,
                    "Resource": resources,
                }
            ],
        }
    )
    policy_input = {
        "policy_document": policy_string,
        "policy_sha256": sha256(policy_string.encode()).hexdigest(),
    }
    return PolicyModel(**policy_input)


async def _generate_change(
    principal_arn: str,
    resource_arns: List[str],
    actions: List[str],
    is_new: bool = True,
):
    policy_document = await _generate_iam_policy(resource_arns, actions)
    change_details = {
        "change_type": ChangeType.inline_policy,
        "arn": principal_arn,
        "resource_arns": resource_arns,
        "policy_name": "foobar",
        "new": is_new,
        "policy": policy_document,
        "policy_sha256": "",
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
    TODO(psanders): Read in action maps from config instead of hard coding

    :param action_groups:
    :param action_map:
    :return:
    """
    actions: List[str] = []
    for ag in action_groups:
        actions += action_map.get(ag, [])
    return actions


async def generate_generic_change(
    generator: GenericChangeGeneratorModel,
) -> InlinePolicyChangeModel:
    action_map = config.get("self_service_iam.change_types.generic.actions")
    if not action_map:
        raise MissingConfigurationValue(
            "Unable to find applicable action map configuration."
        )
    access_level_actions: List[str] = []
    for access in generator.access_level:
        access_level_actions.append(action_map.get(access))
    actions = await _get_access_level_actions_for_resource(
        generator.resource, access_level_actions
    )
    return await _generate_change(generator.arn, [generator.resource], actions)


async def generate_s3_change(
    generator: S3ChangeGeneratorModel,
) -> InlinePolicyChangeModel:
    action_map = config.get("self_service_iam.change_types.s3.actions")
    if not action_map:
        raise MissingConfigurationValue(
            "Unable to find applicable action map configuration."
        )
    resource_arns = []

    # Handle the bucket ARN
    if not generator.resource.startswith("arn:aws:s3:::"):
        generator.resource = f"arn:aws:s3:::{generator.resource}"
    resource_arns.append(generator.resource)

    # Handle the prefix ARN
    if generator.bucket_prefix:
        # Make sure prefix starts with "/"
        if not generator.bucket_prefix.startswith("/"):
            generator.bucket_prefix = f"/{generator.bucket_prefix}"

        # Make sure prefix ends in /*
        # TODO: What if we want to access a single file?
        if not generator.bucket_prefix.endswith("/*"):
            generator.bucket_prefix = f"{generator.bucket_prefix}/*"
    else:
        generator.bucket_prefix = "/*"
    resource_arns.append(f"{generator.resource}{generator.bucket_prefix}")

    action_group_actions: List[str] = []
    for action in generator.action_groups:
        action_group_actions.append(action)
    actions = await _get_actions_from_groups(action_group_actions, action_map)
    return await _generate_change(generator.arn, resource_arns, actions)


async def generate_sns_change(
    generator: SNSChangeGeneratorModel,
) -> InlinePolicyChangeModel:
    action_map = config.get("self_service_iam.change_types.sns.actions")
    if not action_map:
        raise MissingConfigurationValue(
            "Unable to find applicable action map configuration."
        )
    action_group_actions: List[str] = []
    for action in generator.action_groups:
        action_group_actions.append(action)
    actions = await _get_actions_from_groups(action_group_actions, action_map)
    return await _generate_change(generator.arn, [generator.resource], actions)


async def generate_sqs_change(
    generator: SQSChangeGeneratorModel,
) -> InlinePolicyChangeModel:
    action_map = config.get("self_service_iam.change_types.sqs.actions")
    if not action_map:
        raise MissingConfigurationValue(
            "Unable to find applicable action map configuration."
        )
    action_group_actions: List[str] = []
    for action in generator.action_groups:
        action_group_actions.append(action)
    actions = await _get_actions_from_groups(action_group_actions, action_map)
    return await _generate_change(generator.arn, [generator.resource], actions)

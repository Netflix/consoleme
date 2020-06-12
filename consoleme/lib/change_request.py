from hashlib import sha256
from typing import Dict, List

import ujson as json
from policy_sentry.querying.actions import get_actions_with_access_level
from policy_sentry.util.arns import get_service_from_arn

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

generic_access_level_map = {
    # Mapping actions that our model accepts to what sentry expects
    "read": "Read",
    "write": "Write",
    "list": "List",
    "tagging": "Tagging",
    "permissions-management": "Permissions Management",
}

s3_action_map = {
    "list": ["s3:ListBucket", "s3:ListBucketVersions"],
    "get": [
        "s3:GetObject",
        "s3:GetObjectTagging",
        "s3:GetObjectVersion",
        "s3:GetObjectVersionTagging",
        "s3:GetObjectAcl",
        "s3:GetObjectVersionAcl",
    ],
    "put": [
        "s3:PutObject",
        "s3:PutObjectTagging",
        "s3:PutObjectVersionTagging",
        "s3:ListMultipartUploadParts*",
        "s3:AbortMultipartUpload",
        "s3:RestoreObject",
    ],
    "delete": [
        "s3:DeleteObject",
        "s3:DeleteObjectTagging",
        "s3:DeleteObjectVersion",
        "s3:DeleteObjectVersionTagging",
    ],
}

sqs_action_map = {
    "get_queue_attributes": ["sqs:GetQueueAttributes", "sqs:GetQueueUrl"],
    "send_messages": ["sqs:SendMessage"],
    "receive_messages": ["sqs:ReceiveMessage"],
    "delete_messages": ["sqs:DeleteMessage"],
    "set_queue_attributes": ["sqs:SetQueueAttributes"],
}

sns_action_map = {
    "get_topic_attributes": ["sns:GetEndpointAttributes", "sns:GetTopicAttributes"],
    "publish": ["sns:Publish"],
    "subscribe": ["sns:Subscribe", "sns:ConfirmSubscription"],
    "unsubscribe": ["sns:Unsubscribe"],
}


def get_resource_policy_changes(
    principal_arn: str, changes: List[ChangeModel],
) -> List[ResourcePolicyChangeModel]:
    pass


def _generate_iam_policy(
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


def _generate_change(
    principal_arn: str,
    resource_arns: List[str],
    actions: List[str],
    is_new: bool = True,
):
    policy_document = _generate_iam_policy(resource_arns, actions)
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


def _get_access_level_actions_for_resource(
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


def _get_actions_from_groups(
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


def generate_generic_change(
    generator: GenericChangeGeneratorModel,
) -> InlinePolicyChangeModel:
    access_level_actions: List[str] = []
    for access in generator.access_level:
        access_level_actions.append(generic_access_level_map.get(access.value))
    actions = _get_access_level_actions_for_resource(
        generator.resource, access_level_actions
    )
    return _generate_change(generator.arn, [generator.resource], actions,)


def generate_s3_change(generator: S3ChangeGeneratorModel) -> InlinePolicyChangeModel:
    resource_arns = [generator.resource]
    if generator.bucket_prefix is not None:
        resource_arns.append(generator.resource + generator.bucket_prefix)
    action_group_actions: List[str] = []
    for action in generator.action_groups:
        action_group_actions.append(action.value)
    actions = _get_actions_from_groups(action_group_actions, s3_action_map)
    return _generate_change(generator.arn, resource_arns, actions,)


def generate_sns_change(generator: SNSChangeGeneratorModel) -> InlinePolicyChangeModel:
    action_group_actions: List[str] = []
    for action in generator.action_groups:
        action_group_actions.append(action.value)
    actions = _get_actions_from_groups(action_group_actions, sns_action_map)
    return _generate_change(generator.arn, [generator.resource], actions,)


def generate_sqs_change(generator: SQSChangeGeneratorModel) -> InlinePolicyChangeModel:
    action_group_actions: List[str] = []
    for action in generator.action_groups:
        action_group_actions.append(action.value)
    actions = _get_actions_from_groups(action_group_actions, sqs_action_map)
    return _generate_change(generator.arn, [generator.resource], actions,)

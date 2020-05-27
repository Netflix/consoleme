from hashlib import sha256
from typing import Dict, List

from policy_sentry.util.arns import get_service_from_arn
from policy_sentry.querying.actions import get_actions_with_access_level
import ujson as json

from consoleme.models import (
    ChangeModel,
    ChangeType,
    InlinePolicyChangeModel,
    PolicyModel,
    ResourcePolicyChangeModel,
    GenericChangeGeneratorModel,
    S3ChangeGeneratorModel,
    SNSChangeGeneratorModel,
    SQSChangeGeneratorModel,
)

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
    "get": ["sqs:GetQueueAttributes", "sqs:GetQueueUrl"],
    "send": ["sqs:SendMessage"],
    "receive": ["sqs:ReceiveMessage"],
    "delete": ["sqs:DeleteMessage"],
    "set": ["sqs:SetQueueAttributes"],
}

sns_action_map = {
    "get": ["sns:GetEndpointAttributes", "sns:GetTopicAttributes"],
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
    resource_arn: str,
    actions: List[str],
    additional_arns: List[str] = [],
    is_new: bool = True,
):
    resources = [resource_arn] + additional_arns
    policy_document = _generate_iam_policy(resources, actions)
    change_details = {
        "change_type": ChangeType.inline_policy,
        "arn": principal_arn,
        "resource_arn": resource_arn,
        "additional_arns": additional_arns,
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
    actions = _get_access_level_actions_for_resource(
        generator.resource, generator.access_level
    )
    return _generate_change(generator.arn, generator.resource, actions,)


def generate_s3_change(generator: S3ChangeGeneratorModel) -> InlinePolicyChangeModel:
    prefix_arn = generator.resource + generator.bucket_prefix
    additional_arns = [prefix_arn]
    actions = _get_actions_from_groups(generator.action_groups, s3_action_map)
    return _generate_change(
        generator.arn, generator.resource, actions, additional_arns=additional_arns,
    )


def generate_sns_change(generator: SNSChangeGeneratorModel) -> InlinePolicyChangeModel:
    actions = _get_actions_from_groups(generator.action_groups, sns_action_map)
    return _generate_change(generator.arn, generator.resource, actions,)


def generate_sqs_change(generator: SQSChangeGeneratorModel) -> InlinePolicyChangeModel:
    actions = _get_actions_from_groups(generator.action_groups, sqs_action_map)
    return _generate_change(generator.arn, generator.resource, actions,)

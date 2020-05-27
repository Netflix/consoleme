from hashlib import sha256
from typing import Dict, List

import ujson as json

from consoleme.models import (
    ChangeModel,
    ChangeType,
    InlinePolicyChangeModel,
    PolicyModel,
    ResourcePolicyChangeModel,
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


def generate_iam_policy(
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
    action_groups: List[str],
    action_map: Dict[str, List[str]],
    additional_arns: List[str] = [],
    is_new: bool = True,
):
    actions: List[str] = []
    for ag in action_groups:
        actions += action_map.get(ag, [])

    resources = [resource_arn] + additional_arns
    policy_document = generate_iam_policy(resources, actions)
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


def generate_s3_change(generator: S3ChangeGeneratorModel) -> InlinePolicyChangeModel:
    prefix_arn = generator.resource + generator.bucket_prefix
    additional_arns = [prefix_arn]
    return _generate_change(
        generator.arn,
        generator.resource,
        generator.action_groups,
        s3_action_map,
        additional_arns=additional_arns,
    )


def generate_sns_change(generator: SNSChangeGeneratorModel) -> InlinePolicyChangeModel:
    return _generate_change(
        generator.arn, generator.resource, generator.action_groups, sns_action_map,
    )


def generate_sqs_change(generator: SQSChangeGeneratorModel) -> InlinePolicyChangeModel:
    return _generate_change(
        generator.arn, generator.resource, generator.action_groups, sqs_action_map,
    )

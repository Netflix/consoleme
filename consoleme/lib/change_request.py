from typing import Dict, List

from hashlib import sha256
import ujson as json

from consoleme.models import ChangeModel
from consoleme.models import ChangeType
from consoleme.models import InlinePolicyChangeModel
from consoleme.models import ResourcePolicyChangeModel
from consoleme.models import PolicyModel
from consoleme.models import S3ChangeGeneratorModel

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


def generate_s3_change(generator: S3ChangeGeneratorModel) -> InlinePolicyChangeModel:
    prefix_arn = generator.resource + generator.bucket_prefix
    resources = [generator.resource, prefix_arn]
    actions = []
    for ag in generator.action_groups:
        actions += s3_action_map.get(ag, [])
    policy_document = generate_iam_policy(resources, actions)
    change_details = {
        "change_type": ChangeType.inline_policy,
        "arn": generator.arn,
        "resource_arn": generator.resource,
        "additional_arns": prefix_arn,
        "policy_name": "foobar",
        "new": True,
        "policy": policy_document,
        "policy_sha256": "",
    }
    return InlinePolicyChangeModel(**change_details)

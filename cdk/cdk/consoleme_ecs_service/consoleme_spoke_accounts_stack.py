"""
Spoke accounts stack for running ConsoleMe on ECS
"""

import boto3

from aws_cdk import (
    aws_iam as iam,
    core as cdk
)

from constants import SPOKE_BASE_NAME


class ConsolemeSpokeAccountsStack(cdk.Stack):
    """
    Spoke accounts stack for running ConsoleMe on ECS
    Granting the neccesary permissions for ConsoleMe main account role
    """

    def __init__(self, scope: cdk.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        trusted_role_arn = 'arn:aws:iam::' + \
                           boto3.client('sts').get_caller_identity().get(
                               'Account') + ':role/ConsolemeTaskRole'

        spoke_role = iam.Role(
            self,
            f'{SPOKE_BASE_NAME}TrustRole',
            role_name='ConsolemeTrustRole',
            assumed_by=iam.ArnPrincipal(arn=trusted_role_arn)
        )

        spoke_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "autoscaling:Describe*",
                    "cloudwatch:Get*",
                    "cloudwatch:List*",
                    "config:BatchGet*",
                    "config:List*",
                    "config:Select*",
                    "ec2:describeregions",
                    "ec2:DescribeSubnets",
                    "ec2:describevpcendpoints",
                    "ec2:DescribeVpcs",
                    "iam:*",
                    "s3:GetBucketPolicy",
                    "s3:GetBucketTagging",
                    "s3:ListAllMyBuckets",
                    "s3:ListBucket",
                    "s3:PutBucketPolicy",
                    "s3:PutBucketTagging",
                    "sns:GetTopicAttributes",
                    "sns:ListTagsForResource",
                    "sns:ListTopics",
                    "sns:SetTopicAttributes",
                    "sns:TagResource",
                    "sns:UnTagResource",
                    "sqs:GetQueueAttributes",
                    "sqs:GetQueueUrl",
                    "sqs:ListQueues",
                    "sqs:ListQueueTags",
                    "sqs:SetQueueAttributes",
                    "sqs:TagQueue",
                    "sqs:UntagQueue"
                ],
                resources=['*']
            )
        )

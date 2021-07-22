"""
Spoke accounts stack for running ConsoleMe on ECS
"""

from aws_cdk import aws_iam as iam
from aws_cdk import core as cdk

from consoleme_ecs_cdk.service.constants import MAIN_ACCOUNT_ID, SPOKE_BASE_NAME


class ConsolemeSpokeAccountsStack(cdk.Stack):
    """
    Spoke accounts stack for running ConsoleMe on ECS
    Granting the necessary permissions for ConsoleMe main account role
    """

    def __init__(self, scope: cdk.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        trusted_role_arn = "arn:aws:iam::" + MAIN_ACCOUNT_ID + ":role/ConsoleMeTaskRole"

        spoke_role = iam.Role(
            self,
            f"{SPOKE_BASE_NAME}TrustRole",
            role_name="ConsoleMeTrustRole",
            assumed_by=iam.ArnPrincipal(arn=trusted_role_arn),
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
                    "sqs:UntagQueue",
                ],
                resources=["*"],
            )
        )

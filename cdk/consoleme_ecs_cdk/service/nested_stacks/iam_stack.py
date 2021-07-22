"""
IAM stack for running ConsoleMe on ECS
"""

from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from aws_cdk import core as cdk


class IAMStack(cdk.NestedStack):
    """
    IAM stack for running ConsoleMe on ECS
    """

    def __init__(
        self, scope: cdk.Construct, id: str, s3_bucket: s3.Bucket, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Define IAM roles and policies

        ecs_task_role = iam.Role(
            self,
            "TaskRole",
            role_name="ConsoleMeTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )

        ecs_task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "access-analyzer:*",
                    "cloudtrail:*",
                    "cloudwatch:*",
                    "config:SelectResourceConfig",
                    "config:SelectAggregateResourceConfig",
                    "dynamodb:batchgetitem",
                    "dynamodb:batchwriteitem",
                    "dynamodb:deleteitem",
                    "dynamodb:describe*",
                    "dynamodb:getitem",
                    "dynamodb:getrecords",
                    "dynamodb:getsharditerator",
                    "dynamodb:putitem",
                    "dynamodb:query",
                    "dynamodb:scan",
                    "dynamodb:updateitem",
                    "secretsmanager:GetResourcePolicy",
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret",
                    "secretsmanager:ListSecretVersionIds",
                    "secretsmanager:ListSecrets",
                    "sns:createplatformapplication",
                    "sns:createplatformendpoint",
                    "sns:deleteendpoint",
                    "sns:deleteplatformapplication",
                    "sns:getendpointattributes",
                    "sns:getplatformapplicationattributes",
                    "sns:listendpointsbyplatformapplication",
                    "sns:publish",
                    "sns:setendpointattributes",
                    "sns:setplatformapplicationattributes",
                    "sts:assumerole",
                ],
                resources=["*"],
            )
        )

        ecs_task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ses:sendemail", "ses:sendrawemail"],
                resources=["*"],
            )
        )

        ecs_task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "autoscaling:Describe*",
                    "cloudwatch:Get*",
                    "cloudwatch:List*",
                    "config:BatchGet*",
                    "config:List*",
                    "config:Select*",
                    "ec2:DescribeSubnets",
                    "ec2:describevpcendpoints",
                    "ec2:DescribeVpcs",
                    "iam:GetAccountAuthorizationDetails",
                    "iam:ListAccountAliases",
                    "iam:ListAttachedRolePolicies",
                    "ec2:describeregions",
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

        ecs_task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[s3_bucket.bucket_arn, s3_bucket.bucket_arn + "/*"],
            )
        )

        trust_role = iam.Role(
            self,
            "TrustRole",
            role_name="ConsoleMeTrustRole",
            assumed_by=iam.ArnPrincipal(arn=ecs_task_role.role_arn),
        )

        trust_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "access-analyzer:*",
                    "cloudtrail:*",
                    "cloudwatch:*",
                    "config:SelectResourceConfig",
                    "config:SelectAggregateResourceConfig",
                    "dynamodb:batchgetitem",
                    "dynamodb:batchwriteitem",
                    "dynamodb:deleteitem",
                    "dynamodb:describe*",
                    "dynamodb:getitem",
                    "dynamodb:getrecords",
                    "dynamodb:getsharditerator",
                    "dynamodb:putitem",
                    "dynamodb:query",
                    "dynamodb:scan",
                    "dynamodb:updateitem",
                    "sns:createplatformapplication",
                    "sns:createplatformendpoint",
                    "sns:deleteendpoint",
                    "sns:deleteplatformapplication",
                    "sns:getendpointattributes",
                    "sns:getplatformapplicationattributes",
                    "sns:listendpointsbyplatformapplication",
                    "sns:publish",
                    "sns:setendpointattributes",
                    "sns:setplatformapplicationattributes",
                    "sts:assumerole",
                    "autoscaling:Describe*",
                    "cloudwatch:Get*",
                    "cloudwatch:List*",
                    "config:BatchGet*",
                    "config:List*",
                    "config:Select*",
                    "ec2:DescribeSubnets",
                    "ec2:describevpcendpoints",
                    "ec2:DescribeVpcs",
                    "iam:GetAccountAuthorizationDetails",
                    "iam:ListAccountAliases",
                    "iam:ListAttachedRolePolicies",
                    "ec2:describeregions",
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

        ecs_task_execution_role = iam.Role(
            self,
            "TaskExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )

        ecs_task_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_managed_policy_arn(
                self,
                "ServiceRole",
                managed_policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
            )
        )

        create_configuration_lambda_role = iam.Role(
            self,
            "CreateConfigurationFileLambdaRole",
            assumed_by=iam.ServicePrincipal(service="lambda.amazonaws.com"),
        )

        create_configuration_lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_managed_policy_arn(
                self,
                "ConfigurationBasicExecution",
                managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
            )
        )

        create_configuration_lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:PutObject", "s3:DeleteObject"],
                resources=[s3_bucket.bucket_arn + "/*"],
            )
        )

        self.ecs_task_role = ecs_task_role
        self.ecs_task_execution_role = ecs_task_execution_role
        self.create_configuration_lambda_role = create_configuration_lambda_role

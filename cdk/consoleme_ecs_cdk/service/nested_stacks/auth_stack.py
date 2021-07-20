"""
Authentication stack for running ConsoleMe on ECS
"""

from aws_cdk import aws_cognito as cognito
from aws_cdk import core as cdk
from aws_cdk import custom_resources as cr

from consoleme_ecs_cdk.service.constants import (
    ADMIN_TEMP_PASSWORD,
    APPLICATION_PREFIX,
    APPLICATION_SUFFIX,
)


class AuthStack(cdk.NestedStack):
    """
    Authentication stack for running ConsoleMe on ECS
    """

    def __init__(
        self, scope: cdk.Construct, id: str, domain_name: str, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # User pool and user pool OAuth client

        cognito_user_pool = cognito.UserPool(
            self, "UserPool", removal_policy=cdk.RemovalPolicy.DESTROY
        )

        cognito.UserPoolDomain(
            self,
            "UserPoolDomain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=APPLICATION_PREFIX + "-" + APPLICATION_SUFFIX
            ),
            user_pool=cognito_user_pool,
        )

        cognito_admin_user = cr.AwsCustomResource(
            self,
            "UserPoolAdminUserResource",
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
            on_create=cr.AwsSdkCall(
                service="CognitoIdentityServiceProvider",
                action="adminCreateUser",
                parameters={
                    "UserPoolId": cognito_user_pool.user_pool_id,
                    "Username": "consoleme_admin",
                    "UserAttributes": [
                        {"Name": "email", "Value": "consoleme_admin@" + domain_name}
                    ],
                    "TemporaryPassword": ADMIN_TEMP_PASSWORD,
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    cognito_user_pool.user_pool_id
                ),
            ),
        )

        cognito_admin_group = cr.AwsCustomResource(
            self,
            "UserPoolAdminGroupResource",
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
            on_create=cr.AwsSdkCall(
                service="CognitoIdentityServiceProvider",
                action="createGroup",
                parameters={
                    "UserPoolId": cognito_user_pool.user_pool_id,
                    "GroupName": "consoleme_admins",
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    id="UserPoolAdminGroupResource"
                ),
            ),
        )

        cr.AwsCustomResource(
            self,
            "UserPoolUserGroupResource",
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
            on_create=cr.AwsSdkCall(
                service="CognitoIdentityServiceProvider",
                action="createGroup",
                parameters={
                    "UserPoolId": cognito_user_pool.user_pool_id,
                    "GroupName": "consoleme_users",
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    id="UserPoolUserGroupResource"
                ),
            ),
        )

        cognito_assign_admin_group = cr.AwsCustomResource(
            self,
            "UserPoolAssignAdminGroupResource",
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
            on_create=cr.AwsSdkCall(
                service="CognitoIdentityServiceProvider",
                action="adminAddUserToGroup",
                parameters={
                    "UserPoolId": cognito_user_pool.user_pool_id,
                    "GroupName": "consoleme_admins",
                    "Username": "consoleme_admin",
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    id="UserPoolAssignAdminGroupResource"
                ),
            ),
        )

        cognito_assign_admin_group.node.add_dependency(cognito_admin_user)
        cognito_assign_admin_group.node.add_dependency(cognito_admin_group)

        self.cognito_user_pool = cognito_user_pool

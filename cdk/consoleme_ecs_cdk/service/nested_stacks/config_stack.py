"""
Configuration stack for running ConsoleMe on ECS
"""

from uuid import uuid4

import yaml
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_elasticache as ec
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import core as cdk
from aws_cdk import custom_resources as cr

from consoleme_ecs_cdk.service.helpers import create_dependencies_layer


class ConfigStack(cdk.NestedStack):
    """
    Configuration stack for running ConsoleMe on ECS
    """

    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        cognito_user_pool: cognito.UserPool,
        s3_bucket_name: str,
        create_configuration_lambda_role_arn: str,
        redis: ec.CfnCacheCluster,
        domain_name: str,
        **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        config_yaml = yaml.load(open("config.yaml"), Loader=yaml.FullLoader)
        spoke_accounts = config_yaml.get("spoke_accounts", [])

        cognito_user_pool_client = cognito.UserPoolClient(
            self,
            "UserPoolClient",
            user_pool=cognito_user_pool,
            generate_secret=True,
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.COGNITO
            ],
            prevent_user_existence_errors=True,
            o_auth=cognito.OAuthSettings(
                callback_urls=[
                    "https://" + domain_name + "/auth",
                    "https://" + domain_name + "/oauth2/idpresponse",
                ],
                logout_urls=["https://" + domain_name + "/logout"],
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True, implicit_code_grant=True
                ),
                scopes=[cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL],
            ),
            auth_flows=cognito.AuthFlow(user_password=True, user_srp=True),
        )

        describe_cognito_user_pool_client = cr.AwsCustomResource(
            self,
            "UserPoolClientIDResource",
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
            on_create=cr.AwsSdkCall(
                service="CognitoIdentityServiceProvider",
                action="describeUserPoolClient",
                parameters={
                    "UserPoolId": cognito_user_pool.user_pool_id,
                    "ClientId": cognito_user_pool_client.user_pool_client_id,
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    cognito_user_pool_client.user_pool_client_id
                ),
            ),
            install_latest_aws_sdk=True,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        cognito_user_pool_client_secret = (
            describe_cognito_user_pool_client.get_response_field(
                "UserPoolClient.ClientSecret"
            )
        )

        imported_create_configuration_lambda_role = iam.Role.from_role_arn(
            self,
            "ImportedCreateConfigurationFileLambdaRole",
            role_arn=create_configuration_lambda_role_arn,
        )

        jwt_secret = config_yaml["jwt_secret"]

        create_configuration_lambda = lambda_.Function(
            self,
            "CreateConfigurationFileLambda",
            code=lambda_.Code.from_asset("resources/create_config_lambda"),
            handler="index.handler",
            timeout=cdk.Duration.seconds(30),
            layers=[create_dependencies_layer(self, "create_config_lambda")],
            runtime=lambda_.Runtime.PYTHON_3_8,
            role=imported_create_configuration_lambda_role,
            environment={
                "DEPLOYMENT_BUCKET": s3_bucket_name,
                "JWT_SECRET": jwt_secret,
                "OIDC_CLIENT_ID": cognito_user_pool_client.user_pool_client_id,
                "OIDC_CLIENT_SECRET": cognito_user_pool_client_secret,
                "OIDC_METADATA_URL": "https://cognito-idp."
                + self.region
                + ".amazonaws.com/"
                + cognito_user_pool.user_pool_id
                + "/.well-known/openid-configuration",
                "REDIS_HOST": redis.attr_redis_endpoint_address,
                "SES_IDENTITY_ARN": "arn:aws:ses:"
                + self.region
                + ":"
                + self.account
                + ":identity/"
                + domain_name,
                "SUPPORT_CHAT_URL": "https://discord.gg/nQVpNGGkYu",
                "APPLICATION_ADMIN": "consoleme_admin",
                "ACCOUNT_NUMBER": self.account,
                "ISSUER": domain_name,
                "SPOKE_ACCOUNTS": ",".join(spoke_accounts),
            },
        )

        create_configuration_resource_provider = cr.Provider(
            self,
            "CreateConfigurationFileProvider",
            on_event_handler=create_configuration_lambda,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        cdk.CustomResource(
            self,
            "CreateConfigurationFile",
            service_token=create_configuration_resource_provider.service_token,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            properties={"UUID": str(uuid4())},
        )

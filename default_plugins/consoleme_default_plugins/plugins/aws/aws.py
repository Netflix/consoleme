import asyncio
import ssl
import sys
from datetime import datetime, timedelta

import bleach
import boto3
import requests as requests_sync
import tenacity
import ujson as json
from asgiref.sync import sync_to_async
from botocore.exceptions import ClientError
from cloudaux.aws.iam import (
    get_role_inline_policies,
    get_role_managed_policies,
    list_role_tags,
)
from cloudaux.aws.sts import boto3_cached_conn
from retrying import retry
from tornado.httpclient import AsyncHTTPClient
from tornado.httputil import url_concat

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    NoRoleTemplateException,
    UserRoleLambdaException,
    UserRoleNotAssumableYet,
)
from consoleme.lib.dynamo import IAMRoleDynamoHandler
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.redis import RedisHandler

stats = get_plugin_by_name(config.get("plugins.metrics"))()

log = config.get_logger(__name__)


class Aws:
    """The AWS class handles all interactions with AWS."""

    def __init__(self):
        self.red = RedisHandler().redis_sync()
        self.redis_key = config.get("aws.iamroles_redis_key", "IAM_ROLE_CACHE")
        self.dynamo = IAMRoleDynamoHandler()

    @retry(
        stop_max_attempt_number=3,
        wait_exponential_multiplier=1000,
        wait_exponential_max=1000,
    )
    def _add_role_to_redis(self, role_entry: dict):
        """Add the role to redis with a retry.

        :param role_entry:
        :return:
        """
        self.red.hset(self.redis_key, role_entry["arn"], json.dumps(role_entry))

    @retry(
        stop_max_attempt_number=3,
        wait_exponential_multiplier=1000,
        wait_exponential_max=1000,
    )
    def _fetch_role_from_redis(self, role_arn: str):
        """Fetch the role from redis with a retry.

        :param role_arn:
        :return:
        """
        return self.red.hget(self.redis_key, role_arn)

    @retry(
        stop_max_attempt_number=3,
        wait_exponential_multiplier=1000,
        wait_exponential_max=1000,
    )
    def _invoke_lambda(self, client: object, function_name: str, payload: bytes):
        """Invoke the lambda function for creating the user-roles."""
        return client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=payload,
        )

    async def _cloudaux_to_aws(self, role):
        """Convert the cloudaux get_role into the get_account_authorization_details equivalent."""
        # Pop out the fields that are not required:
        # Arn and RoleName will be popped off later:
        unrequired_fields = ["_version", "MaxSessionDuration"]

        for uf in unrequired_fields:
            role.pop(uf, None)

        # Fix the Managed Policies:
        role["AttachedManagedPolicies"] = list(
            map(
                lambda x: {"PolicyName": x["name"], "PolicyArn": x["arn"]},
                role.get("ManagedPolicies", []),
            )
        )
        role.pop("ManagedPolicies", None)

        # Fix the tags:
        if isinstance(role.get("Tags", {}), dict):
            role["Tags"] = list(
                map(
                    lambda key: {"Key": key, "Value": role["Tags"][key]},
                    role.get("Tags", {}),
                )
            )

        # Note: the instance profile list is verbose -- not transforming it (outside of renaming the field)!
        role["InstanceProfileList"] = role.pop("InstanceProfiles", [])

        # Inline Policies:
        role["RolePolicyList"] = list(
            map(
                lambda name: {
                    "PolicyName": name,
                    "PolicyDocument": role["InlinePolicies"][name],
                },
                role.get("InlinePolicies", {}),
            )
        )
        role.pop("InlinePolicies", None)

        return role

    async def fetch_iam_role(
        self, account_id: str, role_arn: str, force_refresh: bool = False
    ) -> dict:
        """Fetch the IAM Role template from Redis and/or Dynamo.

        :param account_id:
        :param role_arn:
        :return:
        """
        log_data: dict = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "role_arn": role_arn,
            "account_id": account_id,
            "force_refresh": force_refresh,
        }

        result: dict = {}

        if not force_refresh:
            # First check redis:
            result: str = await sync_to_async(self._fetch_role_from_redis)(role_arn)

            if result:
                result: dict = json.loads(result)

                # If this item is less than an hour old, then return it from Redis.
                if result["ttl"] > int(
                    (datetime.utcnow() - timedelta(hours=1)).timestamp()
                ):
                    log_data["message"] = "Role not in Redis -- fetching from DDB."
                    log.debug(log_data)
                    stats.count(
                        "aws.fetch_iam_role.in_redis",
                        tags={"account_id": account_id, "role_arn": role_arn},
                    )
                    result["policy"] = json.loads(result["policy"])
                    return result

            # If not in Redis or it's older than an hour, proceed to DynamoDB:
            result = await sync_to_async(self.dynamo.fetch_iam_role)(
                role_arn, account_id
            )

        # If it's NOT in dynamo, or if we're forcing a refresh, we need to reach out to AWS and fetch:
        if force_refresh or not result.get("Item"):
            if force_refresh:
                log_data["message"] = "Force refresh is enabled. Going out to AWS."
                stats.count(
                    "aws.fetch_iam_role.force_refresh",
                    tags={"account_id": account_id, "role_arn": role_arn},
                )
            else:
                log_data["message"] = "Role is missing in DDB. Going out to AWS."
                stats.count(
                    "aws.fetch_iam_role.missing_dynamo",
                    tags={"account_id": account_id, "role_arn": role_arn},
                )
            log.debug(log_data)
            try:
                tasks = []
                role_name = role_arn.split("/")[-1]
                # Instantiate a cached CloudAux client
                client = await sync_to_async(boto3_cached_conn)(
                    "iam",
                    account_number=account_id,
                    assume_role=config.get("policies.role_name"),
                )
                conn = {
                    "account_number": account_id,
                    "assume_role": config.get("policies.role_name"),
                    "region": config.region,
                }

                role_details = asyncio.ensure_future(
                    sync_to_async(client.get_role)(RoleName=role_name)
                )
                tasks.append(role_details)

                all_tasks = [
                    get_role_managed_policies,
                    get_role_inline_policies,
                    list_role_tags,
                ]

                for t in all_tasks:
                    tasks.append(
                        asyncio.ensure_future(
                            sync_to_async(t)({"RoleName": role_name}, **conn)
                        )
                    )

                responses = asyncio.gather(*tasks)
                result = await responses
                role = result[0]["Role"]
                role["ManagedPolicies"] = result[1]
                role["InlinePolicies"] = result[2]
                role["Tags"] = result[3]

            except ClientError as ce:
                if ce.response["Error"]["Code"] == "NoSuchEntity":
                    # The role does not exist:
                    log_data["message"] = "Role does not exist in AWS."
                    log.error(log_data)
                    stats.count(
                        "aws.fetch_iam_role.missing_in_aws",
                        tags={"account_id": account_id, "role_arn": role_arn},
                    )
                    return None

                else:
                    log_data["message"] = f"Some other error: {ce.response}"
                    log.error(log_data)
                    stats.count(
                        "aws.fetch_iam_role.aws_connection_problem",
                        tags={"account_id": account_id, "role_arn": role_arn},
                    )
                    raise

            # Format the role for DynamoDB and Redis:
            await self._cloudaux_to_aws(role)
            result = {
                "arn": role.get("Arn"),
                "name": role.pop("RoleName"),
                "accountId": account_id,
                "ttl": int((datetime.utcnow() + timedelta(hours=36)).timestamp()),
                "policy": self.dynamo.convert_role_to_json(role),
                "templated": self.red.hget(
                    config.get("templated_roles.redis_key", "TEMPLATED_ROLES_v2"),
                    role.get("Arn").lower(),
                ),
            }

            # Sync with DDB:
            await sync_to_async(self.dynamo.sync_iam_role_for_account)(result)
            log_data["message"] = "Role fetched from AWS, and synced with DDB."
            stats.count(
                "aws.fetch_iam_role.fetched_from_aws",
                tags={"account_id": account_id, "role_arn": role_arn},
            )

        else:
            log_data["message"] = "Role fetched from DDB."
            stats.count(
                "aws.fetch_iam_role.in_dynamo",
                tags={"account_id": account_id, "role_arn": role_arn},
            )

            # Fix the TTL:
            result["Item"]["ttl"] = int(result["Item"]["ttl"])
            result = result["Item"]

        # Update the redis cache:
        stats.count(
            "aws.fetch_iam_role.in_dynamo",
            tags={"account_id": account_id, "role_arn": role_arn},
        )
        await sync_to_async(self._add_role_to_redis)(result)

        log_data["message"] += " Updated Redis."
        log.debug(log_data)

        result["policy"] = json.loads(result["policy"])
        return result

    async def call_user_lambda(
        self, role: str, user_email: str, account_id: str, user_role_name: str = "user"
    ) -> str:
        """Call out to the lambda function to provision the per-user role for the account."""
        # Get the template's name based on the account and user role name:
        accounts = self.get_account_ids_to_names()
        account_name = accounts[account_id][0]
        role_to_fetch = (
            f"arn:aws:iam::{account_id}:role/{account_name}_{user_role_name}"
        )

        # Fetch the role
        role_details = await self.fetch_iam_role(account_id, role_to_fetch)

        # If we did not receive any role details, raise an exception:
        if not role_details:
            raise NoRoleTemplateException(f"Unable to locate {role_to_fetch}")

        # Prepare the payload for the lambda and send it out:
        payload = json.dumps(
            {
                "user_role_short_name": role.split("role/")[1],
                "user_email": user_email,
                "account_number": account_id,
                "primary_policies": role_details["policy"].get("RolePolicyList", []),
                "managed_policy_arns": role_details["policy"].get(
                    "AttachedManagedPolicies", []
                ),
            }
        ).encode()

        client = boto3.client("lambda", region_name=config.region)

        lambda_result = await sync_to_async(self._invoke_lambda)(
            client,
            config.get("lambda_role_creator.function_name", "UserRoleCreator"),
            payload,
        )
        lambda_result = json.loads(lambda_result["Payload"].read().decode())

        if not lambda_result.get("success", False):
            raise UserRoleLambdaException(f"Received invalid response: {lambda_result}")

        return f'arn:aws:iam::{lambda_result["account_number"]}:role/{lambda_result["role_name"]}'

    @tenacity.retry(
        wait=tenacity.wait_fixed(2),
        stop=tenacity.stop_after_attempt(5),
        retry=tenacity.retry_if_exception_type(UserRoleNotAssumableYet),
    )
    async def get_credentials(
        self,
        user: str,
        role: str,
        enforce_ip_restrictions: bool = True,
        user_role: bool = False,
        account_id: str = None,
        custom_ip_restrictions: list = None,
    ) -> dict:
        """Get Credentials will return the list of temporary credentials from AWS."""
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": user,
            "role": role,
            "enforce_ip_restrictions": enforce_ip_restrictions,
            "custom_ip_restrictions": custom_ip_restrictions,
            "message": "Generating credentials",
        }
        session = boto3.Session()
        client = session.client("sts", region_name=config.region)

        ip_restrictions = config.get("aws.ip_restrictions")
        stats.count("aws.get_credentials", tags={"role": role, "user": user})

        # If this is a dynamic request, then we need to fetch the role details, call out to the lambda
        # wait for it to complete, assume the role, and then return the assumed credentials back.
        if user_role:
            stats.count("aws.call_user_lambda", tags={"role": role, "user": user})
            try:
                role = await self.call_user_lambda(role, user, account_id)
            except Exception as e:
                raise e

        try:
            if enforce_ip_restrictions and ip_restrictions:
                policy = json.dumps(
                    dict(
                        Version="2012-10-17",
                        Statement=[
                            dict(
                                Effect="Deny",
                                Action="*",
                                Resource="*",
                                Condition=dict(
                                    NotIpAddress={"aws:SourceIP": ip_restrictions}
                                ),
                            ),
                            dict(Effect="Allow", Action="*", Resource="*"),
                        ],
                    )
                )

                credentials = await sync_to_async(client.assume_role)(
                    RoleArn=role, RoleSessionName=user.lower(), Policy=policy
                )
                credentials["Credentials"]["Expiration"] = int(
                    credentials["Credentials"]["Expiration"].timestamp()
                )
                return credentials
            if custom_ip_restrictions:
                policy = json.dumps(
                    dict(
                        Version="2012-10-17",
                        Statement=[
                            dict(
                                Effect="Deny",
                                Action="*",
                                Resource="*",
                                Condition=dict(
                                    NotIpAddress={
                                        "aws:SourceIP": custom_ip_restrictions
                                    }
                                ),
                            ),
                            dict(Effect="Allow", Action="*", Resource="*"),
                        ],
                    )
                )

                credentials = await sync_to_async(client.assume_role)(
                    RoleArn=role, RoleSessionName=user.lower(), Policy=policy
                )
                credentials["Credentials"]["Expiration"] = int(
                    credentials["Credentials"]["Expiration"].timestamp()
                )
                return credentials

            credentials = await sync_to_async(client.assume_role)(
                RoleArn=role, RoleSessionName=user.lower()
            )
            credentials["Credentials"]["Expiration"] = int(
                credentials["Credentials"]["Expiration"].timestamp()
            )
            log.debug(log_data)
            return credentials
        except ClientError as e:
            # TODO(ccastrapel): Determine if user role was really just created, or if this is an older role.
            if user_role:
                raise UserRoleNotAssumableYet(e.response["Error"])
            raise

    async def generate_url(
        self,
        user: str,
        role: str,
        region: str = "us-east-1",
        user_role: bool = False,
        account_id: str = None,
    ) -> str:
        """Generate URL will get temporary credentials and craft a URL with those credentials."""
        function = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        log_data = {
            "function": function,
            "user": user,
            "role": role,
            "message": "Generating authenticated AWS console URL",
        }
        log.debug(log_data)
        credentials = await self.get_credentials(
            user,
            role,
            user_role=user_role,
            account_id=account_id,
            enforce_ip_restrictions=False,
        )

        credentials_d = {
            "sessionId": credentials.get("Credentials", {}).get("AccessKeyId"),
            "sessionKey": credentials.get("Credentials", {}).get("SecretAccessKey"),
            "sessionToken": credentials.get("Credentials", {}).get("SessionToken"),
        }

        req_params = {
            "Action": "getSigninToken",
            "Session": bleach.clean(json.dumps(credentials_d)),
            "DurationSeconds": config.get("aws.session_duration", 43200),
        }

        http_client = AsyncHTTPClient(force_instance=True)

        url_with_params: str = url_concat(config.get("aws.federation_url"), req_params)
        r = await http_client.fetch(url_with_params, ssl_options=ssl.SSLContext())
        token = json.loads(r.body)

        login_req_params = {
            "Action": "login",
            "Issuer": config.get("aws.issuer"),
            "Destination": "{}".format(config.get("aws.console_url").format(region)),
            "SigninToken": bleach.clean(token.get("SigninToken")),
            "SessionDuration": config.get("aws.session_duration", 43200),
        }

        r2 = requests_sync.Request(
            "GET",
            config.get(
                "aws.federation_url", "https://signin.aws.amazon.com/federation"
            ),
            params=login_req_params,
        )
        url = r2.prepare().url
        return url

    async def sns_publisher_group_requests(
        self, user, group, justification, request_id, bg_check_passed
    ):
        raise NotImplementedError()

    async def sns_publish_policy_requests(self, request, request_uri):
        raise NotImplementedError()

    async def send_communications_policy_change_request(self, request, send_sns=False):
        """
        Optionally send a notification when there's a new policy change request

        :param request:
        :param send_sns:
        :return:
        """
        log_data: dict = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Function is not configured.",
        }
        log.warning(log_data)
        return

    @staticmethod
    def get_account_ids_to_names():
        return config.get("account_ids_to_name")

    @staticmethod
    def handle_detected_role(role):
        pass

    async def should_auto_approve_policy(self, events, user, user_groups):
        return False


def init():
    """Initialize the AWS plugin."""
    return Aws()

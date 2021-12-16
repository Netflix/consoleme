import asyncio
import copy
import ssl
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

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
    get_user_inline_policies,
    get_user_managed_policies,
    list_role_tags,
)
from cloudaux.aws.sts import boto3_cached_conn
from retrying import retry
from tornado.httpclient import AsyncHTTPClient
from tornado.httputil import url_concat

from consoleme.config import config
from consoleme.exceptions.exceptions import UserRoleNotAssumableYet
from consoleme.lib.aws import raise_if_background_check_required_and_no_background_check
from consoleme.lib.dynamo import IAMRoleDynamoHandler
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.policies import send_communications_policy_change_request_v2
from consoleme.lib.redis import RedisHandler

stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()

log = config.get_logger(__name__)


class Aws:
    """The AWS class handles interactions with AWS."""

    def __init__(self) -> None:
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

    async def cloudaux_to_aws(self, principal):
        """Convert the cloudaux get_role/get_user into the get_account_authorization_details equivalent."""
        # Pop out the fields that are not required:
        # Arn and RoleName/UserName will be popped off later:
        unrequired_fields = ["_version", "MaxSessionDuration"]
        principal_type = principal["Arn"].split(":")[-1].split("/")[0]
        for uf in unrequired_fields:
            principal.pop(uf, None)

        # Fix the Managed Policies:
        principal["AttachedManagedPolicies"] = list(
            map(
                lambda x: {"PolicyName": x["name"], "PolicyArn": x["arn"]},
                principal.get("ManagedPolicies", []),
            )
        )
        principal.pop("ManagedPolicies", None)

        # Fix the tags:
        if isinstance(principal.get("Tags", {}), dict):
            principal["Tags"] = list(
                map(
                    lambda key: {"Key": key, "Value": principal["Tags"][key]},
                    principal.get("Tags", {}),
                )
            )

        # Note: the instance profile list is verbose -- not transforming it (outside of renaming the field)!
        principal["InstanceProfileList"] = principal.pop("InstanceProfiles", [])

        # Inline Policies:
        if principal_type == "role":

            principal["RolePolicyList"] = list(
                map(
                    lambda name: {
                        "PolicyName": name,
                        "PolicyDocument": principal["InlinePolicies"][name],
                    },
                    principal.get("InlinePolicies", {}),
                )
            )
        else:
            principal["UserPolicyList"] = copy.deepcopy(
                principal.pop("InlinePolicies", [])
            )
        principal.pop("InlinePolicies", None)

        return principal

    @staticmethod
    def _get_iam_user_sync(account_id, user_name, conn) -> Optional[Dict[str, Any]]:
        client = boto3_cached_conn(
            "iam",
            account_number=account_id,
            assume_role=config.get("policies.role_name"),
            read_only=True,
            retry_max_attempts=2,
            client_kwargs=config.get("boto3.client_kwargs", {}),
        )
        user = client.get_user(UserName=user_name)["User"]
        user["ManagedPolicies"] = get_user_managed_policies(
            {"UserName": user_name}, **conn
        )
        user["InlinePolicies"] = get_user_inline_policies(
            {"UserName": user_name}, **conn
        )
        user["Tags"] = client.list_user_tags(UserName=user_name)
        user["Groups"] = client.list_groups_for_user(UserName=user_name)
        return user

    @staticmethod
    async def _get_iam_user_async(
        account_id, user_name, conn
    ) -> Optional[Dict[str, Any]]:
        tasks = []
        client = await sync_to_async(boto3_cached_conn)(
            "iam",
            account_number=account_id,
            assume_role=config.get("policies.role_name"),
            read_only=True,
            retry_max_attempts=2,
            client_kwargs=config.get("boto3.client_kwargs", {}),
        )
        user_details = asyncio.ensure_future(
            sync_to_async(client.get_user)(UserName=user_name)
        )
        tasks.append(user_details)

        all_tasks = [
            get_user_managed_policies,
            get_user_inline_policies,
        ]

        for t in all_tasks:
            tasks.append(
                asyncio.ensure_future(sync_to_async(t)({"UserName": user_name}, **conn))
            )

        user_tag_details = asyncio.ensure_future(
            sync_to_async(client.list_user_tags)(UserName=user_name)
        )
        tasks.append(user_tag_details)

        user_group_details = asyncio.ensure_future(
            sync_to_async(client.list_groups_for_user)(UserName=user_name)
        )
        tasks.append(user_group_details)

        responses = asyncio.gather(*tasks)
        async_task_result = await responses
        user = async_task_result[0]["User"]
        user["ManagedPolicies"] = async_task_result[1]
        inline_policies = []
        for name, policy in async_task_result[2].items():
            inline_policies.append({"PolicyName": name, "PolicyDocument": policy})
        user["InlinePolicies"] = inline_policies
        user["Tags"] = async_task_result[3].get("Tags", [])
        user["Groups"] = async_task_result[4].get("Groups", [])
        return user

    @staticmethod
    def get_iam_role_sync(account_id, role_name, conn) -> Optional[Dict[str, Any]]:
        client = boto3_cached_conn(
            "iam",
            account_number=account_id,
            assume_role=config.get("policies.role_name"),
            read_only=True,
            retry_max_attempts=2,
            client_kwargs=config.get("boto3.client_kwargs", {}),
        )
        role = client.get_role(RoleName=role_name)["Role"]
        role["ManagedPolicies"] = get_role_managed_policies(
            {"RoleName": role_name}, **conn
        )
        role["InlinePolicies"] = get_role_inline_policies(
            {"RoleName": role_name}, **conn
        )
        role["Tags"] = list_role_tags({"RoleName": role_name}, **conn)
        return role

    @staticmethod
    async def _get_iam_role_async(
        account_id, role_name, conn
    ) -> Optional[Dict[str, Any]]:
        tasks = []
        client = await sync_to_async(boto3_cached_conn)(
            "iam",
            account_number=account_id,
            assume_role=config.get("policies.role_name"),
            read_only=True,
            retry_max_attempts=2,
            client_kwargs=config.get("boto3.client_kwargs", {}),
        )
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
                asyncio.ensure_future(sync_to_async(t)({"RoleName": role_name}, **conn))
            )

        responses = asyncio.gather(*tasks)
        async_task_result = await responses
        role = async_task_result[0]["Role"]
        role["ManagedPolicies"] = async_task_result[1]
        role["InlinePolicies"] = async_task_result[2]
        role["Tags"] = async_task_result[3]
        return role

    async def fetch_iam_user(
        self,
        account_id: str,
        user_arn: str,
        run_sync=False,
    ) -> Optional[Dict[str, Any]]:
        """Fetch the IAM User from AWS in threadpool if run_sync=False, otherwise synchronously.

        :param account_id:
        :param user_arn:
        :return:
        """
        log_data: dict = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user_arn": user_arn,
            "account_id": account_id,
        }

        try:
            user_name = user_arn.split("/")[-1]
            conn = {
                "account_number": account_id,
                "assume_role": config.get("policies.role_name"),
                "region": config.region,
                "client_kwargs": config.get("boto3.client_kwargs", {}),
            }
            if run_sync:
                user = self._get_iam_user_sync(account_id, user_name, conn)
            else:
                user = await self._get_iam_user_async(account_id, user_name, conn)

        except ClientError as ce:
            if ce.response["Error"]["Code"] == "NoSuchEntity":
                # The user does not exist:
                log_data["message"] = "User does not exist in AWS."
                log.error(log_data)
                stats.count(
                    "aws.fetch_iam_user.missing_in_aws",
                    tags={"account_id": account_id, "user_arn": user_arn},
                )
                return None

            else:
                log_data["message"] = f"Some other error: {ce.response}"
                log.error(log_data)
                stats.count(
                    "aws.fetch_iam_user.aws_connection_problem",
                    tags={"account_id": account_id, "user_arn": user_arn},
                )
                raise
        await self.cloudaux_to_aws(user)
        return user

    async def fetch_iam_role(
        self,
        account_id: str,
        role_arn: str,
        force_refresh: bool = False,
        run_sync=False,
    ) -> Optional[Dict[str, Any]]:
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
                role_name = role_arn.split("/")[-1]
                conn = {
                    "account_number": account_id,
                    "assume_role": config.get("policies.role_name"),
                    "region": config.region,
                    "client_kwargs": config.get("boto3.client_kwargs", {}),
                }
                if run_sync:
                    role = self.get_iam_role_sync(account_id, role_name, conn)
                else:
                    role = await self._get_iam_role_async(account_id, role_name, conn)

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
            await self.cloudaux_to_aws(role)
            result = {
                "arn": role.get("Arn"),
                "name": role.pop("RoleName"),
                "resourceId": role.pop("RoleId"),
                "accountId": account_id,
                "ttl": int((datetime.utcnow() + timedelta(hours=36)).timestamp()),
                "policy": self.dynamo.convert_iam_resource_to_json(role),
                "permissions_boundary": role.get("PermissionsBoundary", {}),
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
        raise NotImplementedError("This feature isn't enabled in ConsoleMe OSS")

    @tenacity.retry(
        wait=tenacity.wait_fixed(2),
        stop=tenacity.stop_after_attempt(10),
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
        client = session.client(
            "sts",
            region_name=config.region,
            endpoint_url=config.get(
                "aws.sts_endpoint_url", "https://sts.{region}.amazonaws.com"
            ).format(region=config.region),
        )

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

        await raise_if_background_check_required_and_no_background_check(role, user)

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
                                    NotIpAddress={"aws:SourceIP": ip_restrictions},
                                    Null={
                                        "aws:ViaAWSService": "true",
                                        "aws:PrincipalTag/AWSServiceTrust": "true",
                                    },
                                    StringNotLike={
                                        "aws:PrincipalArn": [
                                            "arn:aws:iam::*:role/aws:*"
                                        ]
                                    },
                                ),
                            ),
                            dict(Effect="Allow", Action="*", Resource="*"),
                        ],
                    )
                )

                credentials = await sync_to_async(client.assume_role)(
                    RoleArn=role,
                    RoleSessionName=user.lower(),
                    Policy=policy,
                    DurationSeconds=config.get("aws.session_duration", 3600),
                )
                credentials["Credentials"]["Expiration"] = int(
                    credentials["Credentials"]["Expiration"].timestamp()
                )
                log.debug(
                    {
                        **log_data,
                        "access_key_id": credentials["Credentials"]["AccessKeyId"],
                    }
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
                                    },
                                    Null={
                                        "aws:ViaAWSService": "true",
                                        "aws:PrincipalTag/AWSServiceTrust": "true",
                                    },
                                    StringNotLike={
                                        "aws:PrincipalArn": [
                                            "arn:aws:iam::*:role/aws:*"
                                        ]
                                    },
                                ),
                            ),
                            dict(Effect="Allow", Action="*", Resource="*"),
                        ],
                    )
                )

                credentials = await sync_to_async(client.assume_role)(
                    RoleArn=role,
                    RoleSessionName=user.lower(),
                    Policy=policy,
                    DurationSeconds=config.get("aws.session_duration", 3600),
                )
                credentials["Credentials"]["Expiration"] = int(
                    credentials["Credentials"]["Expiration"].timestamp()
                )
                log.debug(
                    {
                        **log_data,
                        "access_key_id": credentials["Credentials"]["AccessKeyId"],
                    }
                )
                return credentials

            credentials = await sync_to_async(client.assume_role)(
                RoleArn=role,
                RoleSessionName=user.lower(),
                DurationSeconds=config.get("aws.session_duration", 3600),
            )
            credentials["Credentials"]["Expiration"] = int(
                credentials["Credentials"]["Expiration"].timestamp()
            )
            log.debug(
                {**log_data, "access_key_id": credentials["Credentials"]["AccessKeyId"]}
            )
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
            "DurationSeconds": config.get("aws.session_duration", 3600),
        }

        http_client = AsyncHTTPClient(force_instance=True)

        url_with_params: str = url_concat(
            config.get(
                "aws.federation_url", "https://signin.aws.amazon.com/federation"
            ),
            req_params,
        )
        r = await http_client.fetch(url_with_params, ssl_options=ssl.SSLContext())
        token = json.loads(r.body)

        login_req_params = {
            "Action": "login",
            "Issuer": config.get("aws.issuer"),
            "Destination": (
                "{}".format(
                    config.get(
                        "aws.console_url", "https://{}.console.aws.amazon.com"
                    ).format(region)
                )
            ),
            "SigninToken": bleach.clean(token.get("SigninToken")),
            "SessionDuration": config.get("aws.session_duration", 3600),
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

    async def send_communications_new_policy_request(
        self, extended_request, admin_approved, approval_probe_approved
    ):
        """
        Optionally send a notification when there's a new policy change request

        :param approval_probe_approved:
        :param admin_approved:
        :param extended_request:
        :return:
        """
        await send_communications_policy_change_request_v2(extended_request)
        return

    @staticmethod
    def handle_detected_role(role):
        pass

    async def should_auto_approve_policy_v2(self, extended_request, user, user_groups):
        return {"approved": False}


def init():
    """Initialize the AWS plugin."""
    return Aws()

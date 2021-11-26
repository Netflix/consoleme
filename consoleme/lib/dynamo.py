import asyncio
import os
import sys
import time
import uuid
import zlib
from collections import defaultdict
from datetime import datetime

# used as a placeholder for empty SID to work around this:
# https://github.com/aws/aws-sdk-js/issues/833
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

import bcrypt
import boto3
import sentry_sdk
import simplejson as json
import yaml
from asgiref.sync import sync_to_async
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import Binary  # noqa
from cloudaux import get_iso_string
from cloudaux.aws.sts import boto3_cached_conn
from retrying import retry
from tenacity import Retrying, stop_after_attempt, wait_fixed

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    DataNotRetrievable,
    NoExistingRequest,
    NoMatchingRequest,
    PendingRequestAlreadyExists,
)
from consoleme.lib.crypto import Crypto
from consoleme.lib.password import wait_after_authentication_failure
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.redis import RedisHandler
from consoleme.models import AuthenticationResponse, ExtendedRequestModel

DYNAMO_EMPTY_STRING = "---DYNAMO-EMPTY-STRING---"

# We need to import Decimal to eval the request. This Decimal usage is to prevent lint errors on importing the unused
# Decimal module.
DYNAMODB_EMPTY_DECIMAL = Decimal(0)

POSSIBLE_STATUSES = config.get(
    "possible_statuses",
    ["pending", "approved", "rejected", "cancelled", "expired", "removed"],
)

stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
log = config.get_logger("consoleme")
crypto = Crypto()
red = RedisHandler().redis_sync()


class BaseDynamoHandler:
    """Base class for interacting with DynamoDB."""

    def _get_dynamo_table(self, table_name):
        function: str = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        try:
            # call sts_conn with my client and pass in forced_client
            if config.get("dynamodb_server"):
                resource = boto3.resource(
                    "dynamodb",
                    region_name=config.region,
                    endpoint_url=config.get(
                        "dynamodb_server",
                        config.get("boto3.client_kwargs.endpoint_url"),
                    ),
                )
            else:
                resource = boto3_cached_conn(
                    "dynamodb",
                    service_type="resource",
                    account_number=config.get("aws.account_number"),
                    session_name=config.get("application_name", "consoleme"),
                    region=config.region,
                    client_kwargs=config.get("boto3.client_kwargs", {}),
                )
            table = resource.Table(table_name)
        except Exception as e:
            log.error({"function": function, "error": e}, exc_info=True)
            stats.count(f"{function}.exception")
            return None
        else:
            return table

    def _data_from_dynamo_replace(
        self,
        obj: Union[
            List[Dict[str, Union[Decimal, str]]],
            Dict[str, Union[Decimal, str]],
            str,
            Decimal,
        ],
    ) -> Union[int, Dict[str, Union[int, str]], str, List[Dict[str, Union[int, str]]]]:
        """Traverse a potentially nested object and replace all Dynamo placeholders with actual empty strings

        Args:
            obj (object)

        Returns:
            object: Object with original empty strings

        """
        if isinstance(obj, dict):
            for k in ["aws:rep:deleting", "aws:rep:updateregion", "aws:rep:updatetime"]:
                if k in obj.keys():
                    del obj[k]
            return {k: self._data_from_dynamo_replace(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._data_from_dynamo_replace(elem) for elem in obj]
        else:
            if isinstance(obj, Binary):
                obj = obj.value
            if str(obj) == DYNAMO_EMPTY_STRING:
                obj = ""
            elif isinstance(obj, Decimal):
                obj = int(obj)
            return obj

    def _data_to_dynamo_replace(self, obj: Any) -> Any:
        """Traverse a potentially nested object and replace all instances of an empty string with a placeholder

        Args:
            obj (object)

        Returns:
            object: Object with Dynamo friendly empty strings

        """
        if isinstance(obj, dict):
            for k in ["aws:rep:deleting", "aws:rep:updateregion", "aws:rep:updatetime"]:
                if k in obj.keys():
                    del obj[k]
            return {k: self._data_to_dynamo_replace(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._data_to_dynamo_replace(elem) for elem in obj]
        else:
            if isinstance(obj, Binary):
                return obj
            if str(obj) == "":
                obj = DYNAMO_EMPTY_STRING
            elif type(obj) in [float, int]:
                obj = Decimal(str(obj))
            elif isinstance(obj, datetime):
                obj = Decimal(str(obj.timestamp()))
            return obj

    def parallel_write_table(self, table, data, overwrite_by_pkeys=None):
        if not overwrite_by_pkeys:
            overwrite_by_pkeys = []
        with table.batch_writer(overwrite_by_pkeys=overwrite_by_pkeys) as batch:
            for item in data:
                for attempt in Retrying(stop=stop_after_attempt(3), wait=wait_fixed(2)):
                    with attempt:
                        batch.put_item(Item=self._data_to_dynamo_replace(item))

    def parallel_scan_table(
        self,
        table,
        total_threads=os.cpu_count(),
        dynamodb_kwargs: Optional[Dict[str, Any]] = None,
    ):
        if not dynamodb_kwargs:
            dynamodb_kwargs = {}

        async def _scan_segment(segment, total_segments):
            response = table.scan(
                Segment=segment, TotalSegments=total_segments, **dynamodb_kwargs
            )
            items = response.get("Items", [])

            while "LastEvaluatedKey" in response:
                response = table.scan(
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                    Segment=segment,
                    TotalSegments=total_segments,
                    **dynamodb_kwargs,
                )
                items.extend(self._data_from_dynamo_replace(response["Items"]))

            return items

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = []
        for i in range(total_threads):
            task = asyncio.ensure_future(_scan_segment(i, total_threads))
            tasks.append(task)

        results = loop.run_until_complete(asyncio.gather(*tasks))
        items = []
        for result in results:
            items.extend(result)
        return items

    async def parallel_scan_table_async(
        self,
        table,
        total_threads=os.cpu_count(),
        dynamodb_kwargs: Optional[Dict[str, Any]] = None,
    ):
        if not dynamodb_kwargs:
            dynamodb_kwargs = {}

        async def _scan_segment(segment, total_segments):
            response = table.scan(
                Segment=segment, TotalSegments=total_segments, **dynamodb_kwargs
            )
            items = response.get("Items", [])

            while "LastEvaluatedKey" in response:
                response = table.scan(
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                    Segment=segment,
                    TotalSegments=total_segments,
                    **dynamodb_kwargs,
                )
                items.extend(self._data_from_dynamo_replace(response["Items"]))

            return items

        tasks = []
        for i in range(total_threads):
            task = asyncio.ensure_future(_scan_segment(i, total_threads))
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        items = []
        for result in results:
            items.extend(result)
        return items


class UserDynamoHandler(BaseDynamoHandler):
    def __init__(self, user_email: Optional[str] = None) -> None:
        try:
            self.requests_table = self._get_dynamo_table(
                config.get("aws.requests_dynamo_table", "consoleme_requests_global")
            )
            self.users_table = self._get_dynamo_table(
                config.get("aws.users_dynamo_table", "consoleme_users_global")
            )
            self.group_log = self._get_dynamo_table(
                config.get("aws.group_log_dynamo_table", "consoleme_audit_global")
            )
            self.dynamic_config = self._get_dynamo_table(
                config.get("aws.group_log_dynamo_table", "consoleme_config_global")
            )
            self.policy_requests_table = self._get_dynamo_table(
                config.get(
                    "aws.policy_requests_dynamo_table", "consoleme_policy_requests"
                )
            )
            self.api_health_roles_table = self._get_dynamo_table(
                config.get(
                    "aws.api_health_apps_table_dynamo_table",
                    "consoleme_api_health_apps",
                )
            )
            self.resource_cache_table = self._get_dynamo_table(
                config.get(
                    "aws.resource_cache_dynamo_table", "consoleme_resource_cache"
                )
            )
            self.cloudtrail_table = self._get_dynamo_table(
                config.get("aws.cloudtrail_table", "consoleme_cloudtrail")
            )

            self.notifications_table = self._get_dynamo_table(
                config.get("aws.notifications_table", "consoleme_notifications")
            )

            if user_email:
                self.user = self.get_or_create_user(user_email)
                self.affected_user = self.user
        except Exception:
            if config.get("development"):
                log.error(
                    "Unable to connect to Dynamo. Trying to set user via development configuration",
                    exc_info=True,
                )
                self.user = self.sign_request(
                    {
                        "last_updated": int(time.time()),
                        "username": user_email,
                        "requests": [],
                    }
                )
                self.affected_user = self.user
            else:
                log.error("Unable to get Dynamo table.", exc_info=True)
                raise

    def write_resource_cache_data(self, data):
        self.parallel_write_table(
            self.resource_cache_table, data, ["resourceId", "resourceType"]
        )

    async def get_dynamic_config_yaml(self) -> bytes:
        """Retrieve dynamic configuration yaml."""
        return await sync_to_async(self.get_dynamic_config_yaml_sync)()

    def get_dynamic_config_yaml_sync(self) -> bytes:
        """Retrieve dynamic configuration yaml synchronously"""
        c = b""

        try:
            current_config = self.dynamic_config.get_item(Key={"id": "master"})
            if not current_config:
                return c
            compressed_config = current_config.get("Item", {}).get("config", "")
            if not compressed_config:
                return c
            c = zlib.decompress(compressed_config.value)
        except Exception:  # noqa
            sentry_sdk.capture_exception()
        return c

    def get_dynamic_config_dict(self) -> dict:
        """Retrieve dynamic configuration dictionary that can be merged with primary configuration dictionary."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # if cleanup: 'RuntimeError: There is no current event loop..'
            loop = None
        if loop and loop.is_running():
            current_config_yaml = self.get_dynamic_config_yaml_sync()
        else:
            current_config_yaml = asyncio.run(self.get_dynamic_config_yaml())
        config_d = yaml.safe_load(current_config_yaml)
        return config_d

    async def get_all_api_health_alerts(self) -> list:
        """Return all requests. If a status is specified, only requests with the specified status will be returned.

        :param status:
        :return:
        """
        response: dict = self.api_health_roles_table.scan()
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = self.api_health_roles_table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            items.extend(self._data_from_dynamo_replace(response["Items"]))

        return items

    async def get_api_health_alert_app(self, app_name) -> dict:
        resp: dict = await sync_to_async(self.api_health_roles_table.get_item)(
            Key={"appName": app_name}
        )
        return resp.get("Item", None)

    async def write_api_health_alert_info(self, request, user_email: str):
        """
        Writes a health alert role to the appropriate DynamoDB table
        """
        function: str = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        # enrich request
        request["app_create_time"]: int = int(time.time())
        request["updated_by"]: str = user_email
        request["last_updated"]: int = int(time.time())

        try:
            await sync_to_async(self.api_health_roles_table.put_item)(
                Item=self._data_to_dynamo_replace(request)
            )
        except Exception:
            error = {
                "message": "Unable to add new api_health info request",
                "request": request,
                "function": function,
            }
            log.error(error, exc_info=True)
            raise

        return request

    async def update_api_health_alert_info(
        self, request: dict, user_email=None, update_by=None, last_updated=None
    ):
        """
        Update api_health_alert_info by roleName
        """
        function: str = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )

        # enrich request
        if update_by:
            request["updated_by"] = update_by
        else:
            request["updated_by"] = user_email
        if last_updated:
            request["last_updated"] = last_updated
        else:
            request["last_updated"] = int(time.time())

        try:
            await sync_to_async(self.api_health_roles_table.put_item)(
                Item=self._data_to_dynamo_replace(request)
            )
        except Exception as e:
            error: dict = {
                "function": function,
                "message": "Unable to update api_health_info request",
                "request": request,
                "error": str(e),
            }
            log.error(error, exc_info=True)
            raise Exception(error)
        return request

    async def delete_api_health_alert_info(self, app: str) -> None:
        """
        Delete api_health_alert_info by roleName
        """
        function: str = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )

        try:
            await sync_to_async(self.api_health_roles_table.delete_item)(
                Key={"appName": app}
            )
        except Exception:
            error: dict = {
                "function": function,
                "message": "Unable to delete api_health info",
                "app": app,
            }
            log.error(error, exc_info=True)
            raise

    async def write_policy_request(
        self,
        user_email: str,
        justification: str,
        arn: str,
        policy_name: str,
        policy_changes: dict,
        resources: List[str],
        resource_policies: List[Dict],
        request_time: int = None,
        request_uuid=None,
        policy_status="pending",
        cross_account_request: bool = False,
        dry_run: bool = False,
    ):
        """
        Writes a policy request to the appropriate DynamoDB table
        dry_run will create the request format, but won't actually write it
        Sample run:
        write_policy_request(policy_changes)
        """

        request_time = request_time or int(time.time())

        # Craft the new request json
        timestamp = int(time.time())
        request_id = request_uuid or str(uuid.uuid4())
        new_request = {
            "request_id": request_id,
            "arn": arn,
            "status": policy_status,
            "justification": justification,
            "request_time": request_time,
            "updated_by": user_email,
            "last_updated": timestamp,
            "username": user_email,
            "policy_name": policy_name,
            "policy_changes": json.dumps(policy_changes),
            "resources": resources,
            "resource_policies": resource_policies,
            "cross_account_request": cross_account_request,
        }

        if not dry_run:
            try:
                await sync_to_async(self.policy_requests_table.put_item)(
                    Item=self._data_to_dynamo_replace(new_request)
                )
            except Exception as e:
                error = f"Unable to add new policy request: {new_request}: {str(e)}"
                log.error(error, exc_info=True)
                raise Exception(error)
        else:
            log_data = {
                "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
                "request": new_request,
                "message": "Dry run, skipping adding request to dynamo",
            }
            log.debug(log_data)
        return new_request

    async def write_policy_request_v2(self, extended_request: ExtendedRequestModel):
        """
        Writes a policy request v2 to the appropriate DynamoDB table
        Sample run:
        write_policy_request_v2(request)
        """
        new_request = {
            "request_id": extended_request.id,
            "principal": extended_request.principal.dict(),
            "status": extended_request.request_status.value,
            "justification": extended_request.justification,
            "request_time": extended_request.timestamp,
            "last_updated": int(time.time()),
            "version": "2",
            "extended_request": json.loads(extended_request.json()),
            "username": extended_request.requester_email,
        }

        if extended_request.principal.principal_type == "AwsResource":
            new_request["arn"] = extended_request.principal.principal_arn
        elif extended_request.principal.principal_type == "HoneybeeAwsResourceTemplate":
            repository_name = extended_request.principal.repository_name
            resource_identifier = extended_request.principal.resource_identifier
            new_request["arn"] = f"{repository_name}-{resource_identifier}"
        else:
            raise Exception("Invalid principal type")

        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Writing policy request v2 to Dynamo",
            "request": new_request,
        }
        log.debug(log_data)

        try:
            await sync_to_async(self.policy_requests_table.put_item)(
                Item=self._data_to_dynamo_replace(new_request)
            )
            log_data[
                "message"
            ] = "Successfully finished writing policy request v2 to Dynamo"
            log.debug(log_data)
        except Exception as e:
            log_data["message"] = "Error occurred writing policy request v2 to Dynamo"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            error = f"{log_data['message']}: {str(e)}"
            raise Exception(error)

        return new_request

    async def update_policy_request(self, updated_request):
        """
        Update a policy request by request ID
        Sample run:
        update_policy_request(policy_changes)
        """
        updated_request["last_updated"] = int(time.time())
        try:
            await sync_to_async(self.policy_requests_table.put_item)(
                Item=self._data_to_dynamo_replace(updated_request)
            )
        except Exception as e:
            error = f"Unable to add updated policy request: {updated_request}: {str(e)}"
            log.error(error, exc_info=True)
            raise Exception(error)

        return updated_request

    async def get_policy_requests(self, arn=None, request_id=None):
        """Reads a policy request from the appropriate DynamoDB table"""
        if not arn and not request_id:
            raise Exception("Must pass in ARN or policy request ID")
        if request_id:
            requests = self.policy_requests_table.query(
                KeyConditionExpression="request_id = :ri",
                ExpressionAttributeValues={":ri": request_id},
            )
        else:
            requests = self.policy_requests_table.query(
                KeyConditionExpression="arn = :arn",
                ExpressionAttributeValues={":arn": arn},
            )
        matching_requests = []
        if requests["Items"]:
            items = self._data_from_dynamo_replace(requests["Items"])
            items = await self.convert_policy_requests_to_v3(items)
            matching_requests.extend(items)
        return matching_requests

    async def convert_policy_requests_to_v3(self, requests):
        # Remove this function and calls to this function after a grace period of
        changed = False
        for request in requests:
            if not request.get("version") in ["2"]:
                continue
            if request.get("extended_request") and not request.get("principal"):
                principal_arn = request.pop("arn")
                request["principal"] = {
                    "principal_arn": principal_arn,
                    "principal_type": "AwsResource",
                }
                request["extended_request"]["principal"] = {
                    "principal_arn": principal_arn,
                    "principal_type": "AwsResource",
                }
            request.pop("arn", None)
            changes = (
                request.get("extended_request", {})
                .get("changes", {})
                .get("changes", [])
            )
            for change in changes:
                if not change.get("principal_arn"):
                    continue
                if not change.get("version") in ["2.0", "2", 2]:
                    continue
                change["principal"] = {
                    "principal_arn": change["principal_arn"],
                    "principal_type": "AwsResource",
                }
                change.pop("principal_arn")
                change["version"] = "3.0"
                changed = True
        if changed:
            self.parallel_write_table(self.policy_requests_table, requests)
        return requests

    async def get_all_policy_requests(
        self, status: Optional[str] = "pending"
    ) -> List[Dict[str, Union[int, List[str], str]]]:
        """Return all policy requests. If a status is specified, only requests with the specified status will be
        returned.

        :param status:
        :return:
        """
        requests = await sync_to_async(self.parallel_scan_table)(
            self.policy_requests_table
        )

        requests = await self.convert_policy_requests_to_v3(requests)

        return_value = []
        if status:
            for item in requests:
                if status and item["status"] == status:
                    return_value.append(item)
        else:
            return_value = requests

        return return_value

    async def update_dynamic_config(self, config: str, updated_by: str) -> None:
        """Take a YAML config and writes to DDB (The reason we use YAML instead of JSON is to preserve comments)."""
        # Validate that config loads as yaml, raises exception if not
        yaml.safe_load(config)
        stats.count("update_dynamic_config", tags={"updated_by": updated_by})
        current_config_entry = self.dynamic_config.get_item(Key={"id": "master"})
        if current_config_entry.get("Item"):
            old_config = {
                "id": current_config_entry["Item"]["updated_at"],
                "updated_by": current_config_entry["Item"]["updated_by"],
                "config": current_config_entry["Item"]["config"],
                "updated_at": str(int(time.time())),
            }

            self.dynamic_config.put_item(Item=self._data_to_dynamo_replace(old_config))

        new_config = {
            "id": "master",
            "config": zlib.compress(config.encode()),
            "updated_by": updated_by,
            "updated_at": str(int(time.time())),
        }
        self.dynamic_config.put_item(Item=self._data_to_dynamo_replace(new_config))

    def validate_signature(self, items):
        signature = items.pop("signature")
        if isinstance(signature, Binary):
            signature = signature.value
        json_request = json.dumps(items, sort_keys=True)
        if not crypto.verify(json_request, signature):
            raise Exception(f"Invalid signature for request: {json_request}")

    def sign_request(
        self, user_entry: Dict[str, Union[Decimal, List[str], Binary, str]]
    ) -> Dict[str, Union[Decimal, List[str], str, bytes]]:
        """
        Sign the request and returned request with signature
        :param user_entry:
        :return:
        """
        # Remove old signature if it exists
        user_entry.pop("signature", None)
        user_entry = self._data_from_dynamo_replace(user_entry)
        json_request = json.dumps(user_entry, sort_keys=True, use_decimal=True)
        sig = crypto.sign(json_request)
        user_entry["signature"] = sig
        return user_entry

    async def authenticate_user(self, login_attempt) -> AuthenticationResponse:
        function: str = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        log_data = {
            "function": function,
            "user_email": login_attempt.username,
            "after_redirect_uri": login_attempt.after_redirect_uri,
        }
        user_entry = await sync_to_async(self.users_table.query)(
            KeyConditionExpression="username = :un",
            ExpressionAttributeValues={":un": login_attempt.username},
        )
        user = None

        generic_error = ["User doesn't exist, or password is incorrect. "]

        if user_entry and "Items" in user_entry and len(user_entry["Items"]) == 1:
            user = user_entry["Items"][0]
        if not user:
            delay_error = await wait_after_authentication_failure(
                login_attempt.username
            )
            error = f"Unable to find user: {login_attempt.username}"
            log.error({**log_data, "message": error + delay_error})
            return AuthenticationResponse(
                authenticated=False, errors=generic_error + [delay_error]
            )

        if not user.get("password"):
            delay_error = await wait_after_authentication_failure(
                login_attempt.username
            )
            error = "User exists, but doesn't have a password stored in the database"
            log.error({**log_data, "message": error + delay_error})
            return AuthenticationResponse(
                authenticated=False, errors=generic_error + [delay_error]
            )

        password_hash_matches = bcrypt.checkpw(
            login_attempt.password.encode("utf-8"), user["password"].value
        )
        if not password_hash_matches:
            delay_error = await wait_after_authentication_failure(
                login_attempt.username
            )
            error = "Password does not match. "
            log.error({**log_data, "message": error + delay_error})
            return AuthenticationResponse(
                authenticated=False, errors=generic_error + [delay_error]
            )
        return AuthenticationResponse(
            authenticated=True, username=user["username"], groups=user["groups"]
        )

    def create_user(
        self,
        user_email,
        password: Optional[str] = None,
        groups: Optional[List[str]] = None,
    ):
        if not groups:
            groups = []
        timestamp = int(time.time())
        unsigned_user_entry = {
            "created": timestamp,
            "last_updated": timestamp,
            "username": user_email,
            "requests": [],
            "groups": groups,
        }

        if password:
            pw = bytes(password, "utf-8")
            salt = bcrypt.gensalt()
            unsigned_user_entry["password"] = bcrypt.hashpw(pw, salt)

        user_entry = self.sign_request(unsigned_user_entry)
        try:
            self.users_table.put_item(Item=self._data_to_dynamo_replace(user_entry))
        except Exception as e:
            error = f"Unable to add user submission: {user_entry}: {str(e)}"
            log.error(error, exc_info=True)
            raise Exception(error)
        return user_entry

    def update_user(
        self,
        user_email,
        password: Optional[str] = None,
        groups: Optional[List[str]] = None,
    ):
        if not groups:
            groups = []

        user_ddb = self.users_table.query(
            KeyConditionExpression="username = :un",
            ExpressionAttributeValues={":un": user_email},
        )

        user = None

        if user_ddb and "Items" in user_ddb and len(user_ddb["Items"]) == 1:
            user = user_ddb["Items"][0]

        if not user:
            raise DataNotRetrievable(f"Unable to find user: {user_email}")

        timestamp = int(time.time())

        if password:
            pw = bytes(password, "utf-8")
            salt = bcrypt.gensalt()
            user["password"] = bcrypt.hashpw(pw, salt)

        if groups:
            user["groups"] = groups
        user["last_updated"] = timestamp

        user_entry = self.sign_request(user)
        try:
            self.users_table.put_item(Item=self._data_to_dynamo_replace(user_entry))
        except Exception as e:
            error = f"Unable to add user submission: {user_entry}: {str(e)}"
            log.error(error, exc_info=True)
            raise Exception(error)
        return user_entry

    def delete_user(self, user_email):
        function: str = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        log_data = {"function": function, "user_email": user_email}
        log.debug(log_data)
        user_entry = {"username": user_email}
        try:
            self.users_table.delete_item(Key=self._data_to_dynamo_replace(user_entry))
        except Exception as e:
            error = f"Unable to delete user: {user_entry}: {str(e)}"
            log.error(error, exc_info=True)
            raise Exception(error)

    async def get_user(
        self, user_email: str
    ) -> Optional[Dict[str, Union[Decimal, List[str], Binary, str]]]:
        function: str = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        log_data = {"function": function, "user_email": user_email}

        log.debug(log_data)

        user = self.users_table.query(
            KeyConditionExpression="username = :un",
            ExpressionAttributeValues={":un": user_email},
        )

        if user and "Items" in user and len(user["Items"]) == 1:
            return user["Items"][0]
        return None

    def get_or_create_user(
        self, user_email: str
    ) -> Dict[str, Union[Decimal, List[str], Binary, str]]:
        function: str = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        log_data = {"function": function, "user_email": user_email}

        log.debug(log_data)

        user = self.users_table.query(
            KeyConditionExpression="username = :un",
            ExpressionAttributeValues={":un": user_email},
        )

        items = []

        if user and "Items" in user:
            items = user["Items"]

        if not items:
            return self.create_user(user_email)
        return items[0]

    def resolve_request_ids(
        self, request_ids: List[str]
    ) -> List[Dict[str, Union[int, str]]]:
        requests = []
        for request_id in request_ids:
            request = self.requests_table.query(
                KeyConditionExpression="request_id = :ri",
                ExpressionAttributeValues={":ri": request_id},
            )

            if request["Items"]:
                items = self._data_from_dynamo_replace(request["Items"])
                requests.append(items[0])
            else:
                raise NoMatchingRequest(
                    f"No matching request for request_id: {request_id}"
                )
        return requests

    def add_request_id_to_user(
        self,
        affected_user: Dict[str, Union[Decimal, List[str], Binary, str]],
        request_id: str,
    ) -> None:
        affected_user["requests"].append(request_id)
        self.users_table.put_item(
            Item=self._data_to_dynamo_replace(self.sign_request(affected_user))
        )

    def add_request(
        self,
        user_email: str,
        group: str,
        justification: str,
        request_time: None = None,
        status: str = "pending",
        updated_by: Optional[str] = None,
    ) -> Dict[str, Union[int, str]]:
        """
        Add a user request to the dynamo table

        Sample run:
        add_request("user@example.com", "engtest", "because")

        :param user_email: Email address of user
        :param group: Name of group user is requesting access to
        :param justification:
        :param request_id:
        :param request_time:
        :param status:
        :param updated_by:
        :return:
        """
        """
        Request:
          group
          justification
          role
          request_time
          approval_time
          updated_by
          approval_reason
          status

        user@example.com:
          requests: []
          last_updated: 1
          signature: xxxx
        #pending: []
        #expired: []
        # How to expire requests if soemeone maliciously deletes content
        # How to query for all approved requests for group X
        # What if we want to send email saying your request is expiring in 7 days? Maybe celery to query all
        # What about concept of request ID? Maybe base64 encoded thing?
        # Need an all-in-one page to show all pending requests, all expired/approved requests

      """
        request_time = request_time or int(time.time())

        stats.count("new_group_request", tags={"user": user_email, "group": group})

        if self.affected_user.get("username") != user_email:
            self.affected_user = self.get_or_create_user(user_email)
        # Get current user. Create if they do not already exist
        # self.user = self.get_or_create_user(user_email)
        # Get current user requests, which will validate existing signature
        # existing_request_ids = self.user["requests"]
        # existing_requests = self.resolve_request_ids(existing_request_ids)
        existing_pending_requests_for_group = self.get_requests_by_user(
            user_email, group, status="pending"
        )

        # Craft the new request json
        timestamp = int(time.time())
        request_id = str(uuid.uuid4())
        new_request = {
            "request_id": request_id,
            "group": group,
            "status": status,
            "justification": justification,
            "request_time": request_time,
            "updated_by": updated_by,
            "last_updated": timestamp,
            "username": user_email,
        }

        # See if user already has an active or pending request for the group
        if existing_pending_requests_for_group:
            for request in existing_pending_requests_for_group:
                raise PendingRequestAlreadyExists(
                    f"Pending request for group: {group} already exists: {request}"
                )
        try:
            self.requests_table.put_item(Item=self._data_to_dynamo_replace(new_request))
        except Exception as e:
            error = {
                "error": f"Unable to add user request: {str(e)}",
                "request": new_request,
            }
            log.error(error, exc_info=True)
            raise Exception(error)

        self.add_request_id_to_user(self.affected_user, request_id)

        return new_request

    async def get_all_requests(self, status=None):
        """Return all requests. If a status is specified, only requests with the specified status will be returned.

        :param status:
        :return:
        """
        items = await sync_to_async(self.parallel_scan_table)(self.requests_table)

        return_value = []
        if status:
            for item in items:
                new_json = []
                for j in item["json"]:
                    if j["status"] == status:
                        new_json.append(j)
                item["json"] = new_json
                if new_json:
                    return_value.append(item)
        else:
            return_value = items

        return return_value

    def get_requests_by_user(
        self,
        user_email: str,
        group: str = None,
        status: str = None,
        use_cache: bool = False,
    ) -> dict:
        """Get requests by user. Group and status can also be specified to filter results.
        :param user_email:
        :param group:
        :param status:
        :return:
        """
        red_key = f"USER_REQUESTS_{user_email}-{group}-{status}"

        if use_cache:
            requests_to_return = red.get(red_key)
            if requests_to_return:
                return json.loads(requests_to_return)

        if self.affected_user.get("username") != user_email:
            self.affected_user = self.get_or_create_user(user_email)
        existing_request_ids = self.affected_user["requests"]
        existing_requests = self.resolve_request_ids(existing_request_ids)
        requests_to_return = []
        if existing_requests:
            for request in existing_requests:
                if group and request["group"] != group:
                    continue
                if status and request["status"] != status:
                    continue
                requests_to_return.append(request)
        if use_cache:
            red.setex(red_key, 120, json.dumps(requests_to_return))
        return requests_to_return

    def change_request_status(
        self, user_email, group, new_status, updated_by=None, reviewer_comments=None
    ):
        """

        :param user:
        :param status:
        :param request_id:
        :return:
        """
        stats.count(
            "update_group_request",
            tags={
                "user": user_email,
                "group": group,
                "new_status": new_status,
                "updated_by": updated_by,
            },
        )
        modified_request = None
        if self.affected_user.get("username") != user_email:
            self.affected_user = self.get_or_create_user(user_email)
        timestamp = int(time.time())
        if new_status not in POSSIBLE_STATUSES:
            raise Exception(
                f"Invalid status. Status must be one of {POSSIBLE_STATUSES}"
            )
        if new_status == "approved" and not updated_by:
            raise Exception(
                "You must provide `updated_by` to change a request status to approved."
            )
        existing_requests = self.get_requests_by_user(user_email)
        if existing_requests:
            updated = False
            for request in existing_requests:
                if request["group"] == group:
                    request["updated_by"] = updated_by
                    request["status"] = new_status
                    request["last_updated"] = timestamp
                    request["reviewer_comments"] = reviewer_comments
                    modified_request = request
                    try:
                        self.requests_table.put_item(
                            Item=self._data_to_dynamo_replace(request)
                        )
                    except Exception as e:
                        error = f"Unable to add user request: {request}: {str(e)}"
                        log.error(error, exc_info=True)
                        raise Exception(error)
                    updated = True

            if not updated:
                raise NoExistingRequest(
                    f"Unable to find existing request for user: {user_email} and group: {group}."
                )
        else:
            raise NoExistingRequest(
                f"Unable to find existing requests for user: {user_email}"
            )

        return modified_request

    def change_request_status_by_id(
        self,
        request_id: str,
        new_status: str,
        updated_by: Optional[str] = None,
        reviewer_comments: Optional[str] = None,
    ) -> Dict[str, Union[int, str]]:
        """
        Change request status by ID

        :param request_id:
        :param new_status:
        :param updated_by:
        :return: new requests
        """
        modified_request = None
        if new_status == "approved" and not updated_by:
            raise Exception(
                "You must provide `updated_by` to change a request status to approved."
            )
        requests = self.resolve_request_ids([request_id])

        if new_status not in POSSIBLE_STATUSES:
            raise Exception(
                f"Invalid status. Status must be one of {POSSIBLE_STATUSES}"
            )

        for request in requests:
            request["status"] = new_status
            request["updated_by"] = updated_by
            request["last_updated"] = int(time.time())
            request["reviewer_comments"] = reviewer_comments
            modified_request = request
            try:
                self.requests_table.put_item(Item=self._data_to_dynamo_replace(request))
            except Exception as e:
                error = f"Unable to add user request: {request} : {str(e)}"
                log.error(error, exc_info=True)
                raise Exception(error)
        return modified_request

    def get_all_policies(self):
        """Return all policies."""
        response = self.policies_table.scan()
        items = []

        if response and "Items" in response:
            items = self._data_from_dynamo_replace(response["Items"])

        while "LastEvaluatedKey" in response:
            response = self.policies_table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            items.extend(self._data_from_dynamo_replace(response["Items"]))

        return items

    async def create_group_log_entry(
        self,
        group: str,
        username: str,
        updated_by: str,
        action: str,
        updated_at: None = None,
        extra: None = None,
    ) -> None:
        updated_at = updated_at or int(time.time())

        log_id = str(uuid.uuid4())
        log_entry = {
            "uuid": log_id,
            "group": group,
            "username": username,
            "updated_by": updated_by,
            "updated_at": updated_at,
            "action": action,
            "extra": extra,
        }
        self.group_log.put_item(Item=self._data_to_dynamo_replace(log_entry))

    async def get_all_audit_logs(self) -> List[Dict[str, Union[int, None, str]]]:
        response = await sync_to_async(self.group_log.scan)()
        items = []

        if response and "Items" in response:
            items = self._data_from_dynamo_replace(response["Items"])

        while "LastEvaluatedKey" in response:
            response = await sync_to_async(self.group_log.scan)(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            items.extend(self._data_from_dynamo_replace(response["Items"]))

        return items

    async def get_all_pending_requests(self):
        return await self.get_all_requests(status="pending")

    def batch_write_cloudtrail_events(self, items):
        with self.cloudtrail_table.batch_writer(
            overwrite_by_pkeys=["arn", "request_id"]
        ) as batch:
            for item in items:
                batch.put_item(Item=self._data_to_dynamo_replace(item))
        return True

    async def get_top_cloudtrail_errors_by_arn(self, arn, n=5):
        response: dict = await sync_to_async(self.cloudtrail_table.query)(
            KeyConditionExpression=Key("arn").eq(arn)
        )
        items = response.get("Items", [])
        aggregated_errors = defaultdict(dict)

        for item in items:
            if int(item["ttl"]) < int(time.time()):
                continue
            event_call = item["event_call"]
            event_resource = item.get("resource", "")

            event_string = f"{event_call}|||{event_resource}"
            if not aggregated_errors.get(event_string):
                aggregated_errors[event_string]["count"] = 0
                aggregated_errors[event_string]["generated_policy"] = item.get(
                    "generated_policy", {}
                )
            aggregated_errors[event_string]["count"] += 1

        top_n_errors = {
            k: v
            for k, v in sorted(
                aggregated_errors.items(),
                key=lambda item: item[1]["count"],
                reverse=True,
            )[:n]
        }

        return top_n_errors

    def count_arn_errors(self, error_count, items):
        for item in items:
            arn = item.get("arn")
            if not error_count.get(arn):
                error_count[arn] = 0
            error_count[arn] += item.get("count", 1)
        return error_count


class IAMRoleDynamoHandler(BaseDynamoHandler):
    def __init__(self) -> None:
        try:
            self.role_table = self._get_dynamo_table(
                config.get("aws.iamroles_dynamo_table", "consoleme_iamroles_global")
            )

        except Exception:
            log.error("Unable to get the IAM Role DynamoDB tables.", exc_info=True)
            raise

    @retry(
        stop_max_attempt_number=4,
        wait_exponential_multiplier=1000,
        wait_exponential_max=1000,
    )
    def _update_role_table_value(self, role_ddb: dict) -> None:
        """Run the specific DynamoDB update with retryability."""
        self.role_table.put_item(Item=role_ddb)

    @retry(
        stop_max_attempt_number=4,
        wait_exponential_multiplier=1000,
        wait_exponential_max=1000,
    )
    def fetch_iam_role(self, role_arn: str, account_id: str):
        return self.role_table.get_item(Key={"arn": role_arn, "accountId": account_id})

    def convert_iam_resource_to_json(self, role: dict) -> str:
        return json.dumps(role, default=self._json_encode_timestamps)

    def _json_encode_timestamps(self, field: datetime) -> str:
        """Solve those pesky timestamps and JSON annoyances."""
        if isinstance(field, datetime):
            return get_iso_string(field)

    def sync_iam_role_for_account(self, role_ddb: dict) -> None:
        """Sync the IAM roles received to DynamoDB.

        :param role_ddb:
        :return:
        """
        try:
            # Unfortunately, DDB does not support batch updates :(... So, we need to update each item individually :/
            self._update_role_table_value(role_ddb)

        except Exception as e:
            log_data = {
                "message": "Error syncing Account's IAM roles to DynamoDB",
                "account_id": role_ddb["accountId"],
                "role_ddb": role_ddb,
                "error": str(e),
            }
            log.error(log_data, exc_info=True)
            raise

    def fetch_all_roles(self):
        response = self.role_table.scan()
        items = []

        if response and "Items" in response:
            items = self._data_from_dynamo_replace(response["Items"])
        while "LastEvaluatedKey" in response:
            response = self.role_table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            items.extend(self._data_from_dynamo_replace(response["Items"]))
        return items

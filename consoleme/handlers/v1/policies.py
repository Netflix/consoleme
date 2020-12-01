import re
import sys
from typing import Dict, List, Optional

import sentry_sdk
import tornado.escape
import ujson as json
from policyuniverse.expander_minimizer import _expand_wildcard_action

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    InvalidRequestParameter,
    MustBeFte,
    Unauthorized,
)
from consoleme.handlers.base import BaseAPIV1Handler, BaseHandler, BaseMtlsHandler
from consoleme.lib.account_indexers import get_account_id_to_name_mapping
from consoleme.lib.auth import can_admin_policies
from consoleme.lib.aws import get_resource_policies, get_resource_policy
from consoleme.lib.dynamo import UserDynamoHandler
from consoleme.lib.generic import write_json_error
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.policies import (
    can_move_back_to_pending,
    can_update_requests,
    escape_json,
    get_formatted_policy_changes,
    get_resources_from_events,
    get_url_for_resource,
    parse_policy_change_request,
    update_role_policy,
)
from consoleme.lib.redis import redis_get, redis_hgetall
from consoleme.lib.requests import cache_all_policy_requests

log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics"))()
aws = get_plugin_by_name(config.get("plugins.aws"))()
auth = get_plugin_by_name(config.get("plugins.auth"))()


class PolicyReviewHandler(BaseHandler):
    async def get(self, request_id):
        dynamo: UserDynamoHandler = UserDynamoHandler(self.user)
        requests: List[dict] = await dynamo.get_policy_requests(request_id=request_id)

        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")

        if len(requests) == 0:
            raise Exception("No request found with that ID")
        if len(requests) > 1:
            raise Exception("Duplicate requests found")
        request = requests[0]

        if request and request.get("version") == "2":
            request_id = request["request_id"]
            self.redirect(f"/policies/request_v2/{request_id}")
            return

        arn: str = request.get("arn", "")
        role_name: str = arn.split("/")[1]
        account_id: str = arn.split(":")[4]
        role_uri: str = f"/policies/edit/{account_id}/iamrole/{role_name}"
        justification: str = request.get("justification", "")
        status: str = request.get("status", "")

        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "arn": arn,
            "user": self.user,
            "ip": self.ip,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": request.get("request_id"),
        }
        log.debug(log_data)

        stats.count("PolicyReviewHandler.get", tags={"user": self.user, "arn": arn})

        try:
            formatted_policy_changes = await get_formatted_policy_changes(
                account_id, arn, request
            )
        except Exception as e:
            log.error(
                {**log_data, "error": "Exception while formatting changes"},
                exc_info=True,
            )
            sentry_sdk.capture_exception()
            await write_json_error(e, obj=self)
            await self.finish()
            return
        requestor_info = await auth.get_user_info(request["username"])
        show_approve_reject_buttons = False
        can_cancel: bool = False
        show_update_button: bool = False
        read_only = True

        can_apply_resource_policies = (can_admin_policies(self.user, self.groups),)
        supported_resource_policies = config.get(
            "policies.supported_resource_types_for_policy_application",
            ["s3", "sqs", "sns"],
        )
        resource_policies: List[Dict] = request.get("resource_policies", [])
        for resource_policy in resource_policies:
            resource_type: str = resource_policy.get("type", "")
            resource_region: str = resource_policy.get("region", "")
            resource_name: str = resource_policy.get("resource", "")
            resource_account: str = resource_policy.get("account", "")
            resource_policy["old_policy_document"] = await get_resource_policy(
                resource_account, resource_type, resource_name, resource_region
            )

            # if account wasn't present, we don't support applying resource policies automatically
            # (for backwards compatibility as we can't pull current resource policy and don't want to overwrite)
            if not resource_account or resource_type not in supported_resource_policies:
                resource_policy["supported"] = False
            else:
                resource_policy["supported"] = True
                # only need to provide ARN if resource_type is IAM, which is not supported
                resource_policy["url"] = await get_url_for_resource(
                    arn="",
                    resource_type=resource_type,
                    account_id=resource_account,
                    region=resource_region,
                    resource_name=resource_name,
                )

        if status == "pending":
            show_approve_reject_buttons = (can_admin_policies(self.user, self.groups),)
            show_update_button = await can_update_requests(
                request, self.user, self.groups
            )
            can_cancel = show_update_button
            read_only = False

        show_pending_button = await can_move_back_to_pending(
            request, self.user, self.groups
        )
        await self.render(
            "policy_review.html",
            page_title="ConsoleMe - Policy Review",
            current_page="policies",
            arn=arn,
            account_id=account_id,
            justification=justification,
            changes=formatted_policy_changes["changes"],
            status=status,
            can_cancel=can_cancel,
            user=self.user,
            user_groups=self.groups,
            config=config,
            show_approve_reject_buttons=show_approve_reject_buttons,
            show_cancel_button=can_cancel,
            show_pending_button=show_pending_button,
            show_update_button=show_update_button,
            request=request,
            requestor_info=requestor_info,
            policy_name=formatted_policy_changes["changes"][0][
                "name"
            ],  # TODO: Support multiple policy changes
            role=formatted_policy_changes["role"],
            new_policy=formatted_policy_changes["changes"][0][
                "new_policy"
            ],  # TODO: Support multiple policy changes
            read_only=read_only,
            role_uri=role_uri,
            escape_json=escape_json,
            policy_changes=formatted_policy_changes,
            resource_policies=resource_policies,
            can_apply_resource_policies=can_apply_resource_policies,
        )

    async def post(self, request_id):

        if not self.user:
            return

        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")

        data = tornado.escape.json_decode(self.request.body)

        dynamo: UserDynamoHandler = UserDynamoHandler(self.user)
        requests: List[dict] = await dynamo.get_policy_requests(request_id=request_id)
        original_policy_document: dict = json.loads(
            data.get("original_policy_document")
        )
        updated_policy_document: dict = json.loads(data.get("updated_policy_document"))
        policy_name: str = data.get("policy_name")
        reviewer_comments: str = data.get("reviewer_comments")
        send_email = True

        if len(requests) == 0:
            raise Exception("No request found with that ID")
        if len(requests) > 1:
            raise Exception("Duplicate requests found")
        request: dict = requests[0]
        arn: str = request["arn"]
        account_id: str = arn.split(":")[4]
        current_role = await aws.fetch_iam_role(account_id, arn, force_refresh=True)
        updated_status: str = data.get("updated_status")

        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "arn": arn,
            "user": self.user,
            "ip": self.ip,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": request.get("request_id"),
            "updated_status": updated_status,
        }
        log.debug(log_data)

        stats.count(
            "PolicyReviewHandler.post",
            tags={"user": self.user, "arn": arn, "updated_status": updated_status},
        )

        can_approve_reject = (can_admin_policies(self.user, self.groups),)
        can_change_to_pending = await can_move_back_to_pending(
            request, self.user, self.groups
        )
        result: Dict = {"status": "success"}

        can_update_request: bool = await can_update_requests(
            request, self.user, self.groups
        )
        can_cancel: bool = can_update_request
        if updated_status not in [
            "approved",
            "rejected",
            "pending",
            "update",
            "cancelled",
        ]:
            raise Exception("Invalid status")

        if updated_status == request.get("status"):
            raise Exception(
                f"Status is already equal to {updated_status}. Unable to update request."
            )

        # Prepare to update with the appropriate details. This doesn't mean the request is authorized yet.
        if updated_status != "update":
            request["status"] = updated_status
        if updated_status == "update":
            send_email = False
            if policy_name in [
                "Assume Role Policy Document",
                "AssumeRolePolicyDocument",
            ]:
                edited_document = json.loads(request["policy_changes"])[0][
                    "assume_role_policy_document"
                ]["assume_role_policy_document"]
            else:
                edited_document = json.loads(request["policy_changes"])[0][
                    "inline_policies"
                ][0]["policy_document"]
            if updated_policy_document == edited_document:
                await write_json_error(
                    "No changes were detected in the proposed policy.", obj=self
                )
                return
        request["updated_by"] = self.user

        if updated_status in ["approved", "rejected", "update"]:
            if policy_name in [
                "Assume Role Policy Document",
                "AssumeRolePolicyDocument",
            ]:
                policy_changes = [
                    {
                        "arn": arn,
                        "assume_role_policy_document": {
                            "assume_role_policy_document": updated_policy_document
                        },
                        "requester": request.get("username"),
                    }
                ]
            else:
                policy_changes = [
                    {
                        "arn": arn,
                        "inline_policies": [
                            {
                                "policy_name": policy_name,
                                "policy_document": updated_policy_document,
                            }
                        ],
                        "requester": request.get("username"),
                    }
                ]
            try:
                resource_actions = await get_resources_from_events(policy_changes)
                resource_policies, cross_account_request = await get_resource_policies(
                    arn, resource_actions, account_id
                )
            except Exception as e:
                sentry_sdk.capture_exception()
                log_data["error"] = e
                log.error(log_data, exc_info=True)
                resource_actions = {}
                resource_policies = []
                cross_account_request = False

            log_data["resource_actions"] = resource_actions
            log_data["resource_policies"] = resource_policies
            log.debug(log_data)
            dynamo = UserDynamoHandler(self.user)
            request["resource_policies"] = resource_policies
            request["policy_changes"] = json.dumps(policy_changes)
            request["reviewer_comments"] = reviewer_comments
            request["cross_account_request"] = cross_account_request

        # Keep a record of the policy as it was at the time of the change, for historical record
        if updated_status == "approved":
            request["old_policy"] = json.dumps([original_policy_document])

        if updated_status == "cancelled":
            if not can_cancel:
                raise Unauthorized("Unauthorized to cancel request.")

        elif updated_status in ["approved", "rejected"]:
            if not can_approve_reject:
                raise Unauthorized("Unauthorized to approve or reject request.")

        elif updated_status == "pending":
            if not can_change_to_pending:
                raise Unauthorized("Unauthorized to make request pending.")
        elif updated_status == "update":
            if not can_update_request:
                raise Unauthorized("Unauthorized to update request.")

        if updated_status == "approved":
            # Send any emails with the policy that was applied?
            data_type = (
                "AssumeRolePolicyDocument"
                if policy_name
                in ["Assume Role Policy Document", "AssumeRolePolicyDocument"]
                else "InlinePolicy"
            )
            data_list = [
                {
                    "type": data_type,
                    "name": policy_name,
                    "value": json.dumps(updated_policy_document),
                }
            ]
            # Commit policy
            parsed_policy = await parse_policy_change_request(
                self.user, arn, current_role, data_list
            )

            if parsed_policy["status"] == "error":
                await write_json_error(json.dumps(parsed_policy), obj=self)
                return

            events = parsed_policy["events"]

            result = await update_role_policy(events)

            if result["status"] == "success":
                # if approved, Make sure current policy is the same as the one the user thinks they are updating
                await dynamo.update_policy_request(request)

                await aws.fetch_iam_role(account_id, arn, force_refresh=True)
            else:
                await write_json_error(result, obj=self)
                await self.finish()
                return
            self.write(result)
            await self.finish()
            return

        elif updated_status == "rejected":
            request = await dynamo.update_policy_request(request)
        elif updated_status in ["update", "cancelled", "pending"]:
            request = await dynamo.update_policy_request(request)
        if send_email:
            await aws.send_communications_policy_change_request(request)
        self.write(result)
        await self.finish()
        await cache_all_policy_requests()


class AutocompleteHandler(BaseAPIV1Handler):
    async def get(self):
        """
        /api/v1/policyuniverse/autocomplete/?prefix=
        ---
        get:
            description: Supplies autocompleted permissions for the ace code editor.
            responses:
                200:
                    description: Returns a list of the matching permissions.
        """

        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")

        only_filter_services = False

        if (
            self.request.arguments.get("only_filter_services")
            and self.request.arguments.get("only_filter_services")[0].decode("utf-8")
            == "true"
        ):
            only_filter_services = True

        prefix = self.request.arguments.get("prefix")[0].decode("utf-8") + "*"
        results = _expand_wildcard_action(prefix)
        if only_filter_services:
            # We return known matching services in a format that the frontend expects to see them. We omit the wildcard
            # character returned by policyuniverse.
            services = sorted(
                list(set(r.split(":")[0].replace("*", "") for r in results))
            )
            results = [{"title": service} for service in services]
        else:
            results = [dict(permission=r) for r in results]
        self.write(json.dumps(results))
        await self.finish()


async def filter_resources(filter, resources, max=20):
    if filter:
        regexp = re.compile(r"{}".format(filter.strip()), re.IGNORECASE)
        results: List[str] = []
        for resource in resources:
            try:
                if regexp.search(str(resource.get(filter))):
                    if len(results) == max:
                        return results
                    results.append(resource)
            except re.error:
                # Regex error. Return no results
                pass
        return results
    else:
        return resources


async def handle_resource_type_ahead_request(cls):
    try:
        search_string: str = cls.request.arguments.get("search")[0].decode("utf-8")
    except TypeError:
        cls.send_error(400, message="`search` parameter must be defined")
        return

    try:
        resource_type: str = cls.request.arguments.get("resource")[0].decode("utf-8")
    except TypeError:
        cls.send_error(400, message="`resource_type` parameter must be defined")
        return

    account_id = None
    topic_is_hash = True
    account_id_optional: Optional[List[bytes]] = cls.request.arguments.get("account_id")
    if account_id_optional:
        account_id = account_id_optional[0].decode("utf-8")

    limit: int = 10
    limit_optional: Optional[List[bytes]] = cls.request.arguments.get("limit")
    if limit_optional:
        limit = int(limit_optional[0].decode("utf-8"))

    # By default, we only return the S3 bucket name of a resource and not the full ARN
    # unless you specifically request it
    show_full_arn_for_s3_buckets: Optional[bool] = cls.request.arguments.get(
        "show_full_arn_for_s3_buckets"
    )

    role_name = False
    if resource_type == "s3":
        topic = config.get("redis.s3_bucket_key", "S3_BUCKETS")
    elif resource_type == "sqs":
        topic = config.get("redis.sqs_queues_key", "SQS_QUEUES")
    elif resource_type == "sns":
        topic = config.get("redis.sns_topics_key ", "SNS_TOPICS")
    elif resource_type == "iam_arn":
        topic = config.get("aws.iamroles_redis_key ", "IAM_ROLE_CACHE")
    elif resource_type == "iam_role":
        topic = config.get("aws.iamroles_redis_key ", "IAM_ROLE_CACHE")
        role_name = True
    elif resource_type == "account":
        topic = config.get("swag.redis_key", "SWAG_SETTINGSv2")
        topic_is_hash = False
    elif resource_type == "app":
        topic = config.get("celery.apps_to_roles.redis_key", "APPS_TO_ROLES")
        topic_is_hash = False
    else:
        cls.send_error(404, message=f"Invalid resource_type: {resource_type}")
        return

    if not topic:
        raise InvalidRequestParameter("Invalid resource_type specified")

    if topic_is_hash:
        data = await redis_hgetall(topic)
    else:
        data = await redis_get(topic)

    results: List[Dict] = []

    unique_roles: List[str] = []

    if resource_type == "account":
        account_and_id_list = []
        if not data:
            data = "{}"
        accounts = json.loads(data)
        for k, v in accounts.items():
            account_and_id_list.append(f"{k} ({v})")
        for account in account_and_id_list:
            if search_string.lower() in account.lower():
                results.append({"title": account})
    elif resource_type == "app":
        results = {}
        all_role_arns = []
        all_role_arns_j = await redis_hgetall(
            (config.get("aws.iamroles_redis_key", "IAM_ROLE_CACHE"))
        )
        if all_role_arns_j:
            all_role_arns = all_role_arns_j.keys()
        # ConsoleMe (Account: Test, Arn: arn)
        # TODO: Make this OSS compatible and configurable
        try:
            accounts = await get_account_id_to_name_mapping()
        except Exception as e:  # noqa
            accounts = {}

        app_to_role_map = json.loads(data)
        seen: Dict = {}
        seen_roles = {}
        for app_name, roles in app_to_role_map.items():
            if len(results.keys()) > 9:
                break
            if search_string.lower() in app_name.lower():
                results[app_name] = {"name": app_name, "results": []}
                for role in roles:
                    account_id = role.split(":")[4]
                    account = accounts.get(account_id, "")
                    parsed_app_name = (
                        f"{app_name} on {account} ({account_id}) ({role})]"
                    )
                    if seen.get(parsed_app_name):
                        continue
                    seen[parsed_app_name] = True
                    seen_roles[role] = True
                    results[app_name]["results"].append(
                        {"title": role, "description": account}
                    )
        for role in all_role_arns:
            if len(results.keys()) > 9:
                break
            if search_string.lower() in role.lower():
                if seen_roles.get(role):
                    continue
                account_id = role.split(":")[4]
                account = accounts.get(account_id, "")
                if not results.get("Unknown App"):
                    results["Unknown App"] = {"name": "Unknown App", "results": []}
                results["Unknown App"]["results"].append(
                    {"title": role, "description": account}
                )

    else:
        for k, v in data.items():
            if account_id and k != account_id:
                continue
            if role_name:
                try:
                    r = k.split("role/")[1]
                except IndexError:
                    continue
                if search_string.lower() in r.lower():
                    if r not in unique_roles:
                        unique_roles.append(r)
                        results.append({"title": r})
            elif resource_type == "iam_arn":
                if k.startswith("arn:") and search_string.lower() in k.lower():
                    results.append({"title": k})
            else:
                list_of_items = json.loads(v)
                for item in list_of_items:
                    # A Hack to get S3 to show full ARN, and maintain backwards compatibility
                    # TODO: Fix this in V2 of resource specific typeahead endpoints
                    if resource_type == "s3" and show_full_arn_for_s3_buckets:
                        item = f"arn:aws:s3:::{item}"
                    if search_string.lower() in item.lower():
                        results.append({"title": item, "account_id": k})
                    if len(results) > limit:
                        break
            if len(results) > limit:
                break
    return results


class ApiResourceTypeAheadHandler(BaseMtlsHandler):
    async def get(self):
        if self.requester["name"] not in config.get("api_auth.valid_entities", []):
            raise Exception("Call does not originate from a valid API caller")
        results = await handle_resource_type_ahead_request(self)
        self.write(json.dumps(results))


class ResourceTypeAheadHandler(BaseHandler):
    async def get(self):
        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")
        results = await handle_resource_type_ahead_request(self)
        self.write(json.dumps(results))

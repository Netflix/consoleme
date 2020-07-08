import re
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import quote_plus

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
from consoleme.lib.aws import (
    can_delete_roles,
    fetch_resource_details,
    get_all_iam_managed_policies_for_account,
    get_resource_policies,
)
from consoleme.lib.cache import retrieve_json_data_from_redis_or_s3
from consoleme.lib.dynamo import UserDynamoHandler
from consoleme.lib.generic import write_json_error
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.policies import (
    can_manage_policy_requests,
    can_move_back_to_pending,
    can_update_requests,
    escape_json,
    get_formatted_policy_changes,
    get_resources_from_events,
    get_url_for_resource,
    parse_policy_change_request,
    should_auto_approve_policy,
    update_resource_policy,
    update_role_policy,
)
from consoleme.lib.redis import redis_get, redis_hgetall
from consoleme.lib.timeout import Timeout

log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics"))()
aws = get_plugin_by_name(config.get("plugins.aws"))()
auth = get_plugin_by_name(config.get("plugins.auth"))()
internal_policies = get_plugin_by_name(config.get("plugins.internal_policies"))()


class PolicyViewHandler(BaseHandler):
    async def get(self):
        """
        /policies - User endpoint used to render page that will list all accounts, technologies, and names in tabular format.
        ---
        post:
            description: Renders page that will make XHR request to get technology information
            responses:
                200:
                    description: Renders page that will make subsequent XHR requests
                403:
                    description: User has failed authn/authz.
        """

        if not self.user:
            return

        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")
        stats.count("PolicyViewHandler.get", tags={"user": self.user})

        log_data = {
            "user": self.user,
            "ip": self.ip,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }

        log.debug(log_data)
        await self.render(
            "policies.html",
            page_title="ConsoleMe - Policies",
            current_page="policies",
            user=self.user,
            user_groups=self.groups,
            config=config,
        )


def filter_policies(filter, policies):
    if filter.get("filter"):
        regexp = re.compile(r"{}".format(filter.get("filter").strip()), re.IGNORECASE)
        results = []
        for policy in policies:
            try:
                if regexp.search(str(policy.get(filter.get("field")))):
                    results.append(policy)
            except re.error:
                # Regex error. Return no results
                pass
        return results
    else:
        return policies


class GetPoliciesHandler(BaseHandler):
    """Endpoint for parsing policy information."""

    async def get(self):
        """
        /get_policies/ - Filters and returns items from redis that have policy information.
        ---
        post:
            description: Returns items for which we have a policy view
            responses:
                200:
                    description: returns JSON with filtered items.
                403:
                    description: User has failed authn/authz.
        """

        if not self.user:
            return
        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")
        draw = int(self.request.arguments.get("draw")[0])
        length = int(self.request.arguments.get("length")[0])
        start = int(self.request.arguments.get("start")[0])
        finish = start + length
        account_id_search = self.request.arguments.get("columns[0][search][value]")[
            0
        ].decode("utf-8")
        account_name_search = self.request.arguments.get("columns[1][search][value]")[
            0
        ].decode("utf-8")
        name_search = self.request.arguments.get("columns[2][search][value]")[0].decode(
            "utf-8"
        )
        technology_search = self.request.arguments.get("columns[3][search][value]")[
            0
        ].decode("utf-8")
        template_search = self.request.arguments.get("columns[4][search][value]")[
            0
        ].decode("utf-8")
        error_search = self.request.arguments.get("columns[5][search][value]")[
            0
        ].decode("utf-8")

        policies_d = await retrieve_json_data_from_redis_or_s3(
            redis_key=config.get("policies.redis_policies_key", "ALL_POLICIES"),
            s3_bucket=config.get("cache_policies_table_details.s3.bucket"),
            s3_key=config.get("cache_policies_table_details.s3.file"),
            default=[],
        )

        data = []

        results = policies_d

        if error_search == "errors":
            results = sorted(results, key=lambda i: i["errors"], reverse=True)
            error_search = ""

        filters = [
            {"field": "account_name", "filter": account_name_search},
            {"field": "account_id", "filter": account_id_search},
            {"field": "arn", "filter": name_search},
            {"field": "technology", "filter": technology_search},
            {"field": "templated", "filter": template_search},
            {"field": "errors", "filter": error_search},
        ]

        try:
            with Timeout(seconds=5):
                for f in filters:
                    results = filter_policies(f, results)
        except TimeoutError:
            self.write("Query took too long to run. Check your filter.")
            await self.finish()
            raise

        for policy in results[start:finish]:
            arn = policy.get("arn")
            account_id = policy.get("account_id")
            resource_type = policy.get("technology")
            resource_name = policy.get("arn").split(":")[5]
            # resource_path = ""
            if "/" in resource_name:
                # resource_path = resource_name.split("/")[0]
                resource_name = resource_name.split("/")[1]
            region = arn.split(":")[3]
            if resource_type == "iam" and not arn.split(":")[5].startswith("role/"):
                resource_type = "iam" + arn.split(":")[5].split("/")[0]

            url = await get_url_for_resource(
                arn, resource_type, account_id, region, resource_name
            )

            data.append(
                [
                    account_id,
                    policy.get("account_name"),
                    policy.get("arn"),
                    resource_type,
                    policy.get("templated"),
                    policy.get("errors"),
                    url,
                ]
            )
            if len(data) == length:
                break

        response = {
            "draw": draw,
            "recordsTotal": len(policies_d),
            "recordsFiltered": len(results),
            "data": data,
        }
        self.write(response)
        await self.finish()


class PolicyEditHandler(BaseHandler):
    async def get(self, account_id, role_name):

        if not self.user:
            return
        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")
        read_only = False

        can_save_delete = await can_manage_policy_requests(self.groups)
        can_delete_role = await can_delete_roles(self.groups)
        arn = f"arn:aws:iam::{account_id}:role/{role_name}"

        stats.count("PolicyEditHandler.get", tags={"user": self.user, "arn": arn})

        log_data = {
            "user": self.user,
            "ip": self.ip,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "arn": arn,
        }

        log.debug(log_data)

        force_refresh = (
            True if self.request.arguments.get("refresh", [False])[0] else False
        )

        role = await aws.fetch_iam_role(account_id, arn, force_refresh=force_refresh)
        if not role:
            self.send_error(
                404, message=f"Unable to retrieve the specified role: {role_name}"
            )
            return

        cloudtrail_errors = await internal_policies.get_errors_by_role(
            arn, config.get("policies.number_cloudtrail_errors_to_display", 5)
        )

        cloudtrail_error_uri = None

        cloudtrail_error_uri_base = config.get(
            "cloudtrail_errors.error_messages_by_role_uri"
        )

        if cloudtrail_error_uri_base:
            cloudtrail_error_uri = cloudtrail_error_uri_base.format(arn=arn)

        yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y%m%d")
        s3_query_url = config.get("s3.query_url", "").format(
            yesterday=yesterday,
            role_name=f"'{role_name}'",
            account_id=f"'{account_id}'",
        )
        s3_non_error_query_url = config.get("s3.non_error_query_url", "").format(
            yesterday=yesterday,
            role_name=f"'{role_name}'",
            account_id=f"'{account_id}'",
        )

        s3_error_topic = config.get("redis.s3_errors", "S3_ERRORS")
        all_s3_errors = self.red.get(s3_error_topic)
        s3_errors = []
        if all_s3_errors:
            s3_errors = json.loads(all_s3_errors).get(arn, [])

        all_account_managed_policies = await get_all_iam_managed_policies_for_account(
            account_id
        )
        account_name = await aws.get_account_name_from_account_id(account_id)

        await self.render(
            "policy_editor.html",
            page_title="ConsoleMe - Policy Editor",
            current_page="policies",
            role=role,
            account_id=account_id,
            account_name=account_name,
            cloudtrail_errors=cloudtrail_errors,
            cloudtrail_error_uri=cloudtrail_error_uri,
            user=self.user,
            user_groups=self.groups,
            config=config,
            read_only=read_only,
            can_save_delete=can_save_delete,
            can_delete_role=can_delete_role,
            s3_errors=s3_errors,
            s3_query_url=s3_query_url,
            s3_non_error_query_url=s3_non_error_query_url,
            url_encode=quote_plus,
            all_account_managed_policies=all_account_managed_policies,
        )

    async def post(self, account_id, role_name):
        if not self.user:
            return

        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")

        can_save_delete = await can_manage_policy_requests(self.groups)

        if not can_save_delete:
            raise Unauthorized("You are not authorized to edit policies.")

        arn = f"arn:aws:iam::{account_id}:role/{role_name}"

        stats.count("PolicyEditHandler.post", tags={"user": self.user, "arn": arn})

        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "account_id": account_id,
            "role_name": role_name,
            "arn": arn,
            "user": self.user,
            "ip": self.ip,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        role = await aws.fetch_iam_role(account_id, arn)

        data_list = tornado.escape.json_decode(self.request.body)

        result: dict = await parse_policy_change_request(
            self.user, arn, role, data_list
        )

        if result["status"] == "error":
            await write_json_error(json.dumps(result), obj=self)
            return

        events = result["events"]

        result = await update_role_policy(events)

        if result["status"] == "success":
            await aws.fetch_iam_role(account_id, arn, force_refresh=True)

        self.write(result)
        await self.finish()
        return


class ResourcePolicyEditHandler(BaseHandler):
    async def get(self, account_id, resource_type, region=None, resource_name=None):
        if not self.user:
            return
        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")
        read_only = False

        can_save_delete = await can_manage_policy_requests(self.groups)

        account_id_for_arn: str = account_id
        if resource_type == "s3":
            account_id_for_arn = ""
        arn = f"arn:aws:{resource_type}:{region or ''}:{account_id_for_arn}:{resource_name}"

        stats.count(
            "ResourcePolicyEditHandler.get", tags={"user": self.user, "arn": arn}
        )

        log_data = {
            "user": self.user,
            "ip": self.ip,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "arn": arn,
        }

        log.debug(log_data)

        resource_details = await fetch_resource_details(
            account_id, resource_type, resource_name, region
        )

        # TODO: Get S3 errors for s3 buckets only, else CT errors
        yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y%m%d")
        s3_query_url = config.get("s3.bucket_query_url")
        all_s3_errors = None

        if s3_query_url:
            s3_query_url = s3_query_url.format(
                yesterday=yesterday, bucket_name=f"'{resource_name}'"
            )
            s3_error_topic = config.get("redis.s3_errors", "S3_ERRORS")
            all_s3_errors = self.red.get(s3_error_topic)

        s3_errors = []
        if all_s3_errors:
            s3_errors = json.loads(all_s3_errors).get(arn, [])

        await self.render(
            "resource_policy_editor.html",
            page_title="ConsoleMe - Resource Policy Editor",
            current_page="policies",
            arn=arn,
            resource_details=resource_details,
            account_id=account_id,
            user=self.user,
            user_groups=self.groups,
            config=config,
            read_only=read_only,
            can_save_delete=can_save_delete,
            s3_errors=s3_errors,
            s3_query_url=s3_query_url,
            url_encode=quote_plus,
        )

    async def post(self, account_id, resource_type, region=None, resource_name=None):
        if not self.user:
            return

        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")

        can_save_delete = await can_manage_policy_requests(self.groups)

        if not can_save_delete:
            raise Unauthorized("You are not authorized to edit policies.")

        account_id_for_arn: str = account_id
        if resource_type == "s3":
            account_id_for_arn = ""
        arn = f"arn:aws:{resource_type}:{region or ''}:{account_id_for_arn}:{resource_name}"

        stats.count(
            "ResourcePolicyEditHandler.post", tags={"user": self.user, "arn": arn}
        )

        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "account_id": account_id,
            "arn": arn,
            "user": self.user,
            "ip": self.ip,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        resource_details = await fetch_resource_details(
            account_id, resource_type, resource_name, region
        )

        data_list = tornado.escape.json_decode(self.request.body)

        result: dict = await update_resource_policy(
            arn, resource_type, account_id, region, data_list, resource_details
        )
        self.write(result)
        await self.finish()
        return


class PolicyReviewSubmitHandler(BaseHandler):
    async def post(self):

        if not self.user:
            return

        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")

        data: dict = tornado.escape.json_decode(self.request.body)

        arn: str = data.get("arn", "")
        account_id: str = data.get("account_id", "")
        justification: str = data.get("justification", "")
        if not justification:
            await write_json_error(
                "Justification is required to submit a policy change request.", obj=self
            )
            return
        data_list = data.get("data_list", [])
        if len(data_list) != 1:
            raise InvalidRequestParameter("Exactly one change is required per request.")
        policy_name: str = data_list[0].get("name")

        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "arn": arn,
            "user": self.user,
            "ip": self.ip,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "auto_approved": False,
        }
        log.debug(log_data)

        stats.count(
            "PolicyReviewSubmitHandler.post", tags={"user": self.user, "arn": arn}
        )

        role = await aws.fetch_iam_role(account_id, arn)

        parsed_policy_change = await parse_policy_change_request(
            self.user, arn, role, data_list
        )

        if parsed_policy_change["status"] == "error":
            await write_json_error(json.dumps(parsed_policy_change), obj=self)
            return

        events = parsed_policy_change["events"]
        policy_status = "pending"
        should_auto_approve_request: bool = await should_auto_approve_policy(
            events, self.user, self.groups
        )
        if should_auto_approve_request is not False:
            policy_status = "approved"
            log_data["auto_approved"] = True
        try:
            resource_actions = await get_resources_from_events(events)
            resources = list(resource_actions.keys())
            resource_policies, cross_account_request = await get_resource_policies(
                arn, resource_actions, account_id
            )
        except Exception as e:
            config.sentry.captureException()
            log_data["error"] = e
            log.error(log_data, exc_info=True)
            resource_actions = {}
            resources = []
            resource_policies = []
            cross_account_request = False

        log_data["resource_actions"] = resource_actions
        log_data["resource_policies"] = resource_policies
        dynamo = UserDynamoHandler(self.user)
        request = await dynamo.write_policy_request(
            self.user,
            justification,
            arn,
            policy_name,
            events,
            resources,
            resource_policies,
            cross_account_request=cross_account_request,
        )
        if policy_status == "approved":
            try:
                formatted_policy_changes = await get_formatted_policy_changes(
                    account_id, arn, request
                )
            except Exception as e:
                config.sentry.captureException()
                await write_json_error(e, obj=self)
                await self.finish()
                return
            original_policy_document = formatted_policy_changes["changes"][0]["old"]
            request["old_policy"] = json.dumps([original_policy_document])
            result: dict = await update_role_policy(events)
            if result["status"] == "success":
                request["status"] = "approved"
                request[
                    "updated_by"
                ] = f"Auto-Approve Probe: {should_auto_approve_request['approving_probe']}"
                # if approved, Make sure current policy is the same as the one the user thinks they are updating
                await dynamo.update_policy_request(request)
                await aws.fetch_iam_role(account_id, arn, force_refresh=True)
            else:
                await write_json_error(result, obj=self)
                await self.finish()
                return
        await aws.send_communications_policy_change_request(request, send_sns=True)
        request["status"] = "success"
        self.write(request)
        log_data["finished"] = True
        log.debug(log_data)
        await self.finish()
        return


class PolicyReviewHandler(BaseHandler):
    async def get(self, request_id):

        if not self.user:
            return
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
            await write_json_error(e, obj=self)
            await self.finish()
            return
        requestor_info = await auth.get_user_info(request["username"])
        show_approve_reject_buttons = False
        can_cancel: bool = False
        show_update_button: bool = False
        read_only = True
        resource_policies: List = request.get("resource_policies", [])

        if status == "pending":
            show_approve_reject_buttons = await can_manage_policy_requests(self.groups)
            show_update_button = await can_update_requests(
                request, self.user, self.groups
            )
            can_cancel = show_update_button
            read_only = False

        show_pending_button = await can_move_back_to_pending(request, self.groups)
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

        can_approve_reject = await can_manage_policy_requests(self.groups)
        can_change_to_pending = await can_move_back_to_pending(request, self.groups)
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
                config.sentry.captureException()
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


class SelfServiceHandler(BaseHandler):
    async def get(self):
        """
        /self_service_v1
        ---
        get:
            description: Entry point to Self Service IAM Wizard
            responses:
                200:
                    description: Returns Self Service IAM Wizard
        """

        await self.render(
            "self_service.html",
            page_title="ConsoleMe - Self Service",
            current_page="policies",
            user=self.user,
            user_groups=self.groups,
            config=config,
        )


class SelfServiceV2Handler(BaseHandler):
    async def get(self):
        """
        /self_service
        ---
        get:
            description: Entry point to Self Service IAM Wizard
            responses:
                200:
                    description: Returns Self Service IAM Wizard
        """

        await self.render(
            "self_service_v2.html",
            page_title="ConsoleMe - Self Service",
            current_page="policies",
            user=self.user,
            user_groups=self.groups,
            config=config,
        )


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

    if not data:
        return []

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

        accounts = aws.get_account_ids_to_names()
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
                    account = accounts.get(account_id, [""])[0]
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
                account = accounts.get(account_id, [""])[0]
                results[role] = {
                    "name": role.replace("arn:aws:iam::", "").replace(":role", ""),
                    "results": [{"title": role, "description": account}],
                }
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
        if self.requester["name"] not in config.get("api_auth.valid_entities"):
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

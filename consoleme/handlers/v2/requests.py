import asyncio
import sys
import time
import uuid

import sentry_sdk
import ujson as json
from policy_sentry.util.arns import parse_arn
from pydantic import ValidationError

from consoleme.celery_tasks.celery_tasks import app as celery_app
from consoleme.config import config
from consoleme.exceptions.exceptions import (
    InvalidRequestParameter,
    MustBeFte,
    NoMatchingRequest,
    ResourceNotFound,
    Unauthorized,
)
from consoleme.handlers.base import BaseAPIV2Handler, BaseHandler
from consoleme.lib.auth import can_admin_policies
from consoleme.lib.aws import get_resource_account
from consoleme.lib.cache import retrieve_json_data_from_redis_or_s3
from consoleme.lib.dynamo import UserDynamoHandler
from consoleme.lib.generic import filter_table, write_json_error
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.policies import (
    can_move_back_to_pending_v2,
    can_update_cancel_requests_v2,
    get_url_for_resource,
    should_auto_approve_policy_v2,
)
from consoleme.lib.timeout import Timeout
from consoleme.lib.v2.requests import (
    generate_request_from_change_model_array,
    is_request_eligible_for_auto_approval,
    parse_and_apply_policy_request_modification,
    populate_cross_account_resource_policies,
    populate_old_policies,
)
from consoleme.models import (
    CommentModel,
    DataTableResponse,
    ExtendedRequestModel,
    PolicyRequestModificationRequestModel,
    RequestCreationModel,
    RequestCreationResponse,
    RequestStatus,
)

stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
log = config.get_logger()
aws = get_plugin_by_name(config.get("plugins.aws", "default_aws"))()


class RequestHandler(BaseAPIV2Handler):
    """Handler for /api/v2/request

    Allows for creation of a request.
    """

    allowed_methods = ["POST"]

    def on_finish(self) -> None:
        if self.request.method != "POST":
            return
        celery_app.send_task(
            "consoleme.celery_tasks.celery_tasks.cache_policy_requests"
        )
        celery_app.send_task(
            "consoleme.celery_tasks.celery_tasks.cache_credential_authorization_mapping"
        )

    async def post(self):
        """
        POST /api/v2/request

        Request example JSON: (Request Schema is RequestCreationModel in models.py)

        {
          "changes": {
            "changes": [
              {
                "principal_arn": "arn:aws:iam::123456789012:role/curtisTestRole1",
                "change_type": "inline_policy",
                "action": "attach",
                "policy": {
                  "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                      {
                        "Action": [
                          "s3:ListMultipartUploadParts*",
                          "s3:ListBucket"
                        ],
                        "Effect": "Allow",
                        "Resource": [
                          "arn:aws:s3:::curtis-nflx-test/*",
                          "arn:aws:s3:::curtis-nflx-test"
                        ],
                        "Sid": "cmccastrapel159494014dsd1shak"
                      },
                      {
                        "Action": [
                          "ec2:describevolumes",
                          "ec2:detachvolume",
                          "ec2:describelicenses",
                          "ec2:AssignIpv6Addresses",
                          "ec2:reportinstancestatus"
                        ],
                        "Effect": "Allow",
                        "Resource": [
                          "*"
                        ],
                        "Sid": "cmccastrapel1594940141hlvvv"
                      },
                      {
                        "Action": [
                          "sts:AssumeRole"
                        ],
                        "Effect": "Allow",
                        "Resource": [
                          "arn:aws:iam::123456789012:role/curtisTestInstanceProfile"
                        ],
                        "Sid": "cmccastrapel1596483596easdits"
                      }
                    ]
                  }
                }
              },
              {
                "principal_arn": "arn:aws:iam::123456789012:role/curtisTestRole1",
                "change_type": "assume_role_policy",
                "policy": {
                  "policy_document": {
                    "Statement": [
                      {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {
                          "AWS": "arn:aws:iam::123456789012:role/consolemeInstanceProfile"
                        },
                        "Sid": "AllowConsoleMeProdAssumeRolses"
                      }
                    ],
                    "Version": "2012-10-17"
                  }
                }
              },
              {
                "principal_arn": "arn:aws:iam::123456789012:role/curtisTestRole1",
                "change_type": "managed_policy",
                "policy_name": "ApiProtect",
                "action": "attach",
                "arn": "arn:aws:iam::123456789012:policy/ApiProtect"
              },
              {
                "principal_arn": "arn:aws:iam::123456789012:role/curtisTestRole1",
                "change_type": "managed_policy",
                "policy_name": "TagProtect",
                "action": "detach",
                "arn": "arn:aws:iam::123456789012:policy/TagProtect"
              },
              {
                "principal_arn": "arn:aws:iam::123456789012:role/curtisTestRole1",
                "change_type": "inline_policy",
                "policy_name": "random_policy254",
                "action": "attach",
                "policy": {
                  "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                      {
                        "Action": [
                          "ec2:AssignIpv6Addresses"
                        ],
                        "Effect": "Allow",
                        "Resource": [
                          "*"
                        ],
                        "Sid": "cmccastrapel1594940141shakabcd"
                      }
                    ]
                  }
                }
              }
            ]
          },
          "justification": "testing this out.",
          "admin_auto_approve": false
        }

        Response example JSON: (Response Schema is RequestCreationResponse in models.py)

        {
            "errors": 1,
            "request_created": true,
            "request_id": "0c9fb298-c8ea-4d50-917c-3212da07b3ad",
            "action_results": [
                {
                    "status": "success",
                    "message": "Success description"
                },
                {
                    "status": "error",
                    "message": "Error description"
                }
            ]
        }


        """

        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")

        tags = {"user": self.user}
        stats.count("RequestHandler.post", tags=tags)
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": self.user,
            "message": "Create request initialization",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "ip": self.ip,
            "admin_auto_approved": False,
            "probe_auto_approved": False,
        }
        log.debug(log_data)
        try:
            # Validate the model
            changes = RequestCreationModel.parse_raw(self.request.body)
            extended_request = await generate_request_from_change_model_array(
                changes, self.user
            )
            log_data["request"] = extended_request.dict()
            log.debug(log_data)
            admin_approved = False
            approval_probe_approved = False

            # TODO: Provide a note to the requester that admin_auto_approve will apply the requested policies only.
            # It will not automatically apply generated policies. The administrative user will need to visit the policy
            # Request page to do this manually.
            if changes.admin_auto_approve:
                # make sure user is allowed to use admin_auto_approve
                can_manage_policy_request = (
                    can_admin_policies(self.user, self.groups),
                )
                if can_manage_policy_request:
                    extended_request.request_status = RequestStatus.approved
                    admin_approved = True
                    extended_request.reviewer = self.user
                    self_approval_comment = CommentModel(
                        id=str(uuid.uuid4()),
                        timestamp=int(time.time()),
                        user_email=self.user,
                        user=extended_request.requester_info,
                        last_modified=int(time.time()),
                        text=f"Self-approved by admin: {self.user}",
                    )
                    extended_request.comments.append(self_approval_comment)
                    log_data["admin_auto_approved"] = True
                    log_data["request"] = extended_request.dict()
                    log.debug(log_data)
                    stats.count(
                        f"{log_data['function']}.post.admin_auto_approved",
                        tags={"user": self.user},
                    )
                else:
                    # someone is trying to use admin bypass without being an admin, don't allow request to proceed
                    stats.count(
                        f"{log_data['function']}.post.unauthorized_admin_bypass",
                        tags={"user": self.user},
                    )
                    log_data["message"] = "Unauthorized user trying to use admin bypass"
                    log.error(log_data)
                    await write_json_error("Unauthorized", obj=self)
                    return
            else:
                # If admin auto approve is false, check for auto-approve probe eligibility
                is_eligible_for_auto_approve_probe = (
                    await is_request_eligible_for_auto_approval(
                        extended_request, self.user
                    )
                )
                # If we have only made requests that are eligible for auto-approval probe, check against them
                if is_eligible_for_auto_approve_probe:
                    should_auto_approve_request = await should_auto_approve_policy_v2(
                        extended_request, self.user, self.groups
                    )
                    if should_auto_approve_request["approved"]:
                        extended_request.request_status = RequestStatus.approved
                        approval_probe_approved = True
                        stats.count(
                            f"{log_data['function']}.probe_auto_approved",
                            tags={"user": self.user},
                        )
                        approving_probes = []
                        for approving_probe in should_auto_approve_request[
                            "approving_probes"
                        ]:
                            approving_probe_comment = CommentModel(
                                id=str(uuid.uuid4()),
                                timestamp=int(time.time()),
                                user_email=f"Auto-Approve Probe: {approving_probe['name']}",
                                last_modified=int(time.time()),
                                text=f"Policy {approving_probe['policy']} auto-approved by probe: {approving_probe['name']}",
                            )
                            extended_request.comments.append(approving_probe_comment)
                            approving_probes.append(approving_probe["name"])
                        extended_request.reviewer = (
                            f"Auto-Approve Probe: {','.join(approving_probes)}"
                        )
                        log_data["probe_auto_approved"] = True
                        log_data["request"] = extended_request.dict()
                        log.debug(log_data)

            dynamo = UserDynamoHandler(self.user)
            request = await dynamo.write_policy_request_v2(extended_request)
            log_data["message"] = "New request created in Dynamo"
            log_data["request"] = extended_request.dict()
            log_data["dynamo_request"] = request
            log.debug(log_data)
        except (InvalidRequestParameter, ValidationError) as e:
            log_data["message"] = "Validation Exception"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.validation_exception", tags={"user": self.user}
            )
            self.write_error(400, message="Error validating input: " + str(e))
            if config.get("development"):
                raise
            return
        except Exception as e:
            log_data["message"] = "Unknown Exception occurred while parsing request"
            log.error(log_data, exc_info=True)
            stats.count(f"{log_data['function']}.exception", tags={"user": self.user})
            sentry_sdk.capture_exception(tags={"user": self.user})
            self.write_error(500, message="Error parsing request: " + str(e))
            if config.get("development"):
                raise
            return

        # If here, request has been successfully created
        response = RequestCreationResponse(
            errors=0,
            request_created=True,
            request_id=extended_request.id,
            request_url=f"/policies/request/{extended_request.id}",
            action_results=[],
        )

        # If approved is true due to an auto-approval probe or admin auto-approval, apply the non-autogenerated changes
        if extended_request.request_status == RequestStatus.approved:
            for change in extended_request.changes.changes:
                if change.autogenerated:
                    continue
                policy_request_modification_model = (
                    PolicyRequestModificationRequestModel.parse_obj(
                        {
                            "modification_model": {
                                "command": "apply_change",
                                "change_id": change.id,
                            }
                        }
                    )
                )
                policy_apply_response = (
                    await parse_and_apply_policy_request_modification(
                        extended_request,
                        policy_request_modification_model,
                        self.user,
                        self.groups,
                        int(time.time()),
                        approval_probe_approved,
                    )
                )
                response.errors = policy_apply_response.errors
                response.action_results = policy_apply_response.action_results

            # Update in dynamo
            await dynamo.write_policy_request_v2(extended_request)
            account_id = await get_resource_account(extended_request.arn)

            # Force a refresh of the role in Redis/DDB
            arn_parsed = parse_arn(extended_request.arn)
            if arn_parsed["service"] == "iam" and arn_parsed["resource"] == "role":
                await aws.fetch_iam_role(
                    account_id, extended_request.arn, force_refresh=True
                )
            log_data["request"] = extended_request.dict()
            log_data["message"] = "Applied changes based on approved request"
            log_data["response"] = response.dict()
            log.debug(log_data)

        await aws.send_communications_new_policy_request(
            extended_request, admin_approved, approval_probe_approved
        )
        self.write(response.json())
        await self.finish()
        return


class RequestsHandler(BaseAPIV2Handler):
    """Handler for /api/v2/requests

    Api endpoint to list and filter policy requests.
    """

    allowed_methods = ["POST"]

    async def post(self):
        """
        POST /api/v2/requests
        """
        arguments = {k: self.get_argument(k) for k in self.request.arguments}
        markdown = arguments.get("markdown")
        cache_key = config.get(
            "cache_all_policy_requests.redis_key", "ALL_POLICY_REQUESTS"
        )
        s3_bucket = config.get("cache_policy_requests.s3.bucket")
        s3_key = config.get("cache_policy_requests.s3.file")
        arguments = json.loads(self.request.body)
        filters = arguments.get("filters")
        # TODO: Add server-side sorting
        # sort = arguments.get("sort")
        limit = arguments.get("limit", 1000)
        tags = {"user": self.user}
        stats.count("RequestsHandler.post", tags=tags)
        log_data = {
            "function": "RequestsHandler.post",
            "user": self.user,
            "message": "Writing requests",
            "limit": limit,
            "filters": filters,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        requests = await retrieve_json_data_from_redis_or_s3(
            cache_key, s3_bucket=s3_bucket, s3_key=s3_key
        )

        total_count = len(requests)

        if filters:
            try:
                with Timeout(seconds=5):
                    for filter_key, filter_value in filters.items():
                        requests = await filter_table(
                            filter_key, filter_value, requests
                        )
            except TimeoutError:
                self.write("Query took too long to run. Check your filter.")
                await self.finish()
                raise

        if markdown:
            requests_to_write = []
            for request in requests[0:limit]:
                resource_name = request["arn"].split(":")[5]
                if "/" in resource_name:
                    resource_name = resource_name.split("/")[-1]
                region = request["arn"].split(":")[3]
                service_type = request["arn"].split(":")[2]
                account_id = request["arn"].split(":")[4]
                try:
                    url = await get_url_for_resource(
                        request["arn"],
                        service_type,
                        account_id,
                        region,
                        resource_name,
                    )
                except ResourceNotFound:
                    url = None
                # Convert request_id and role ARN to link
                if request.get("version") == "2":
                    request[
                        "request_id"
                    ] = f"[{request['request_id']}](/policies/request/{request['request_id']})"
                # Legacy support for V1 requests. Pending removal.
                else:
                    request[
                        "request_id"
                    ] = f"[{request['request_id']}](/policies/request_v1/{request['request_id']})"
                if url:
                    request["arn"] = f"[{request['arn']}]({url})"
                requests_to_write.append(request)
        else:
            requests_to_write = requests[0:limit]
        filtered_count = len(requests_to_write)
        res = DataTableResponse(
            totalCount=total_count, filteredCount=filtered_count, data=requests_to_write
        )
        self.write(res.json())
        return


class RequestDetailHandler(BaseAPIV2Handler):
    """Handler for /api/v2/requests/{request_id}

    Allows read and update access to a specific request.
    """

    allowed_methods = ["GET", "PUT"]

    def on_finish(self) -> None:
        if self.request.method != "PUT":
            return
        celery_app.send_task(
            "consoleme.celery_tasks.celery_tasks.cache_policy_requests"
        )
        celery_app.send_task(
            "consoleme.celery_tasks.celery_tasks.cache_credential_authorization_mapping"
        )

    async def _get_extended_request(self, request_id, log_data):
        dynamo = UserDynamoHandler(self.user)
        requests = await dynamo.get_policy_requests(request_id=request_id)
        if len(requests) == 0:
            log_data["message"] = "Request with that ID not found"
            log.warn(log_data)
            stats.count(f"{log_data['function']}.not_found", tags={"user": self.user})
            raise NoMatchingRequest(log_data["message"])
        if len(requests) > 1:
            log_data["message"] = "Multiple requests with that ID found"
            log.error(log_data)
            stats.count(
                f"{log_data['function']}.multiple_requests_found",
                tags={"user": self.user},
            )
            raise InvalidRequestParameter(log_data["message"])
        request = requests[0]

        if request.get("version") != "2":
            # Request format is not compatible with this endpoint version
            raise InvalidRequestParameter("Request with that ID is not a v2 request")

        extended_request = ExtendedRequestModel.parse_obj(
            request.get("extended_request")
        )
        return extended_request, request.get("last_updated")

    async def get(self, request_id):
        """
        GET /api/v2/requests/{request_id}
        """
        tags = {"user": self.user}
        stats.count("RequestDetailHandler.get", tags=tags)
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": self.user,
            "message": "Get request details",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "policy_request_id": request_id,
        }
        log.debug(log_data)

        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                self.write_error(
                    403, message="Only FTEs are authorized to view this page."
                )
                return

        try:
            extended_request, last_updated = await self._get_extended_request(
                request_id, log_data
            )
        except InvalidRequestParameter as e:
            sentry_sdk.capture_exception(tags={"user": self.user})
            self.write_error(400, message="Error validating input: " + str(e))
            return
        except NoMatchingRequest as e:
            sentry_sdk.capture_exception(tags={"user": self.user})
            self.write_error(404, message="Error getting request:" + str(e))
            return
        # Run these tasks concurrently.
        concurrent_results = await asyncio.gather(
            populate_old_policies(extended_request, self.user),
            populate_cross_account_resource_policies(extended_request, self.user),
        )
        extended_request = concurrent_results[0]

        populate_cross_account_resource_policies_result = concurrent_results[1]

        if populate_cross_account_resource_policies_result["changed"]:
            extended_request = populate_cross_account_resource_policies_result[
                "extended_request"
            ]
            # Update in dynamo with the latest resource policy changes
            dynamo = UserDynamoHandler(self.user)
            updated_request = await dynamo.write_policy_request_v2(extended_request)
            last_updated = updated_request.get("last_updated")

        can_approve_reject = (can_admin_policies(self.user, self.groups),)
        can_update_cancel = await can_update_cancel_requests_v2(
            extended_request.requester_email, self.user, self.groups
        )
        can_move_back_to_pending = await can_move_back_to_pending_v2(
            extended_request, last_updated, self.user, self.groups
        )

        # In the future request_specific_config will have specific approvers for specific changes based on ABAC
        request_specific_config = {
            "can_approve_reject": can_approve_reject,
            "can_update_cancel": can_update_cancel,
            "can_move_back_to_pending": can_move_back_to_pending,
        }

        template = None
        # Force a refresh of the role in Redis/DDB
        arn_parsed = parse_arn(extended_request.arn)
        if arn_parsed["service"] == "iam" and arn_parsed["resource"] == "role":
            iam_role = await aws.fetch_iam_role(
                arn_parsed["account"], extended_request.arn
            )
            template = iam_role.get("templated")
        response = {
            "request": extended_request.json(),
            "last_updated": last_updated,
            "request_config": request_specific_config,
            "template": template,
        }

        self.write(response)

    async def put(self, request_id):
        """
        PUT /api/v2/requests/{request_id}
        """
        tags = {"user": self.user}
        stats.count("RequestDetailHandler.put", tags=tags)
        log_data = {
            "function": "RequestDetailHandler.put",
            "user": self.user,
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "policy_request_id": request_id,
        }
        log.debug(log_data)

        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")

        try:
            # Validate the request body
            request_changes = PolicyRequestModificationRequestModel.parse_raw(
                self.request.body
            )
            log_data["message"] = "Parsed request body"
            log_data["request"] = request_changes.dict()
            log.debug(log_data)

            extended_request, last_updated = await self._get_extended_request(
                request_id, log_data
            )
            response = await parse_and_apply_policy_request_modification(
                extended_request, request_changes, self.user, self.groups, last_updated
            )

        except (NoMatchingRequest, InvalidRequestParameter, ValidationError) as e:
            log_data["message"] = "Validation Exception"
            log.error(log_data, exc_info=True)
            sentry_sdk.capture_exception(tags={"user": self.user})
            stats.count(
                f"{log_data['function']}.validation_exception", tags={"user": self.user}
            )
            self.write_error(400, message="Error validating input: " + str(e))
            if config.get("development"):
                raise
            return
        except Unauthorized as e:
            log_data["message"] = "Unauthorized"
            log.error(log_data, exc_info=True)
            sentry_sdk.capture_exception(tags={"user": self.user})
            stats.count(
                f"{log_data['function']}.unauthorized", tags={"user": self.user}
            )
            self.write_error(403, message=str(e))
            if config.get("development"):
                raise
            return
        self.write(response.json())
        await self.finish()
        return


class RequestsPageConfigHandler(BaseHandler):
    async def get(self):
        """
        /requests_page_config
        ---
        get:
            description: Retrieve Requests Page Configuration
            responses:
                200:
                    description: Returns Requests Page Configuration
        """
        default_configuration = {
            "pageName": "Requests",
            "pageDescription": "View all IAM policy requests created through ConsoleMe",
            "tableConfig": {
                "expandableRows": True,
                "dataEndpoint": "/api/v2/requests?markdown=true",
                "sortable": False,
                "totalRows": 200,
                "rowsPerPage": 50,
                "serverSideFiltering": True,
                "allowCsvExport": True,
                "allowJsonExport": True,
                "columns": [
                    {
                        "placeholder": "Username",
                        "key": "username",
                        "type": "input",
                        "style": {"width": "100px"},
                    },
                    {
                        "placeholder": "Arn",
                        "key": "arn",
                        "type": "link",
                        "style": {"whiteSpace": "normal", "wordBreak": "break-all"},
                        "width": 3,
                    },
                    {
                        "placeholder": "Request Time",
                        "key": "request_time",
                        "type": "daterange",
                    },
                    {
                        "placeholder": "Status",
                        "key": "status",
                        "type": "dropdown",
                        "style": {"width": "90px"},
                    },
                    {
                        "placeholder": "Request ID",
                        "key": "request_id",
                        "type": "link",
                        "style": {"whiteSpace": "normal", "wordBreak": "break-all"},
                        "width": 2,
                    },
                ],
            },
        }

        table_configuration = config.get(
            "RequestsTableConfigHandler.configuration", default_configuration
        )

        self.write(table_configuration)

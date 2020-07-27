import sys
import time
import uuid

from consoleme.config import config
from consoleme.exceptions.exceptions import InvalidRequestParameter, MustBeFte
from consoleme.handlers.base import BaseAPIV2Handler, BaseHandler
from consoleme.lib.aws import get_resource_account
from consoleme.lib.cache import retrieve_json_data_from_redis_or_s3
from consoleme.lib.dynamo import UserDynamoHandler
from consoleme.lib.generic import filter_table
from consoleme.lib.generic import write_json_error
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.policies import (
    can_manage_policy_requests,
    should_auto_approve_policy_v2,
)
from consoleme.lib.timeout import Timeout
from consoleme.lib.v2.requests import (
    apply_changes_to_role,
    generate_request_from_change_model_array,
    is_request_eligible_for_auto_approval,
)
from consoleme.models import CommentModel, RequestCreationModel, RequestCreationResponse
from pydantic import ValidationError

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()
aws = get_plugin_by_name(config.get("plugins.aws"))()


class RequestHandler(BaseAPIV2Handler):
    """Handler for /api/v2/request

        Allows for creation of a request.
    """

    allowed_methods = ["POST"]

    async def post(self):
        """
        POST /api/v2/request

        Request example JSON: (Request Schema is RequestCreationModel in models.py)

        {
            "justification" : "Justification for making the request"
            "changes" : [
                    {
                        "principal_arn": "arn:aws:iam::123456789012:role/aRole",
                        "change_type": "inline_policy",
                        "resources": [
                            {
                                "arn": "arn:aws:s3:::test",
                                "name": "test",
                                "account_id": "123456789012",
                                "region": "global",
                                "account_name": "",
                                "policy_sha256": null,
                                "policy": null,
                                "owner": null,
                                "approvers": null,
                                "resource_type": "s3",
                                "last_updated": null
                            }
                        ],
                        "status": "not_applied",
                        "version": 2.0,
                        "policy_name": "cm_user_1592499820_gmli",
                        "new": true,
                        "policy": {
                            "version": "2012-10-17",
                            "statements": null,
                            "policy_document": "{\"Version\":\"2012-10-17\",\"Statement\":[[{\"Action\"...",
                            "policy_sha256": "cb300def8dd1deaf4db2bfeef4bc6fc740be18e8ccae74c399affe781f82ba6e"
                        },
                        "old_policy": null
                    }
            ],
            "admin_auto_approve" : "false"
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

        tags = {
            "user": self.user,
        }
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

            if changes.admin_auto_approve:
                # make sure user is allowed to use admin_auto_approve
                can_manage_policy_request = await can_manage_policy_requests(
                    self.groups
                )
                if can_manage_policy_request:
                    extended_request.status = "approved"
                    admin_approved = True
                    extended_request.reviewer = self.user
                    self_approval_comment = CommentModel(
                        id=str(uuid.uuid4()),
                        timestamp=int(time.time()),
                        user_email=self.user,
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
                is_eligible_for_auto_approve_probe = await is_request_eligible_for_auto_approval(
                    extended_request, self.user
                )
                # If we have only made requests that are eligible for auto-approval probe, check against them
                if is_eligible_for_auto_approve_probe:
                    should_auto_approve_request = await should_auto_approve_policy_v2(
                        extended_request, self.user, self.groups
                    )
                    if should_auto_approve_request["approved"]:
                        extended_request.status = "approved"
                        approval_probe_approved = True
                        stats.count(
                            f"{log_data['function']}.probe_auto_approved",
                            tags={"user": self.user},
                        )
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
            return
        except Exception as e:
            log_data["message"] = "Unknown Exception occurred while parsing request"
            log.error(log_data, exc_info=True)
            stats.count(f"{log_data['function']}.exception", tags={"user": self.user})
            config.sentry.captureException(tags={"user": self.user})
            self.write_error(500, message="Error parsing request: " + str(e))
            return

        # If here, request has been successfully created
        response = RequestCreationResponse(
            errors=0,
            request_created=True,
            request_id=extended_request.id,
            action_results=[],
        )

        # If approved is true, could be auto-approval probe or admin auto-approve, apply the changes
        if extended_request.status == "approved":
            await apply_changes_to_role(extended_request, response, self.user)
            # Update in dynamo
            await dynamo.write_policy_request_v2(extended_request)
            account_id = await get_resource_account(extended_request.arn)
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
        sort = arguments.get("sort")
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
        if not sort:
            # Default sort of requests is by request_time descending.
            requests = sorted(
                requests, key=lambda i: i.get("request_time", 0), reverse=True
            )
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
                # Convert request_id and role ARN to link
                request[
                    "request_id"
                ] = f"[{request['request_id']}](/policies/request/{request['request_id']})"
                request[
                    "arn"
                ] = f"[{request['arn']}](/policies/edit/{request['arn'].split(':')[4]}/iamrole/{request['arn'].split('/')[-1]})"
                requests_to_write.append(request)
        else:
            requests_to_write = requests[0:limit]
        self.write(json.dumps(requests_to_write))
        return


class RequestDetailHandler(BaseAPIV2Handler):
    """Handler for /api/v2/requests/{request_id}

    Allows read and update access to a specific request.
    """

    allowed_methods = ["GET", "PUT"]

    async def get(self, request_id):
        """
        GET /api/v2/requests/{request_id}
        """
        tags = {"user": self.user}
        stats.count("RequestDetailHandler.get", tags=tags)
        log_data = {
            "function": "RequestDetailHandler.get",
            "user": self.user,
            "message": "Writing request details",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Get request details")

    async def put(self, request_id):
        """
        PUT /api/v2/requests/{request_id}
        """
        tags = {"user": self.user}
        stats.count("RequestDetailHandler.put", tags=tags)
        log_data = {
            "function": "RequestDetailHandler.put",
            "user": self.user,
            "message": "Updating request details",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Update request details")


class RequestsTableConfigHandler(BaseHandler):
    async def get(self):
        """
        /requests_table_config
        ---
        get:
            description: Retrieve Requests Table Configuration
            responses:
                200:
                    description: Returns Requests Table Configuration
        """
        default_configuration = {
            "expandableRows": True,
            "tableName": "Requests",
            "tableDescription": "View all IAM policy requests created through ConsoleMe",
            "dataEndpoint": "/api/v2/requests?markdown=true",
            "sortable": False,
            "totalRows": 1000,
            "rowsPerPage": 50,
            "serverSideFiltering": True,
            "columns": [
                {"placeholder": "Username", "key": "username", "type": "input"},
                {
                    "placeholder": "Arn",
                    "key": "arn",
                    "type": "input",
                    "style": {"width": "350px"},
                },
                {
                    "placeholder": "Request Time",
                    "key": "request_time",
                    "type": "daterange",
                },
                {"placeholder": "Status", "key": "status", "type": "dropdown"},
                {"placeholder": "Request ID", "key": "request_id", "type": "input"},
                {"placeholder": "Policy Name", "key": "policy_name", "type": "input"},
                {
                    "placeholder": "Last Updated By",
                    "key": "updated_by",
                    "type": "input",
                },
            ],
        }

        table_configuration = config.get(
            "RequestsTableConfigHandler.configuration", default_configuration
        )

        self.write(table_configuration)


class RequestsWebHandler(BaseHandler):
    async def get(self):
        """
        /requests
        ---
        get:
            description: Entry point to Requests view
            responses:
                200:
                    description: Returns Requests view
        """

        await self.render(
            "requests.html",
            page_title="ConsoleMe - Requests",
            current_page="requests",
            user=self.user,
            user_groups=self.groups,
            config=config,
        )

import sys
import time
import uuid

from pydantic import ValidationError

from consoleme.config import config
from consoleme.exceptions.exceptions import InvalidRequestParameter, MustBeFte
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.lib.aws import get_resource_account
from consoleme.lib.dynamo import UserDynamoHandler
from consoleme.lib.generic import write_json_error
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.policies import (
    can_manage_policy_requests,
    should_auto_approve_policy_v2,
)
from consoleme.lib.v2.requests import (
    apply_changes_to_role,
    generate_request_from_change_model_array,
    is_request_eligible_for_auto_approval,
)
from consoleme.models import CommentModel, RequestCreationModel, RequestCreationResponse

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
            log_data["request"] = extended_request.json()
            log.debug(log_data)

            if changes.admin_auto_approve:
                # make sure user is allowed to use admin_auto_approve
                can_manage_policy_request = await can_manage_policy_requests(
                    self.groups
                )
                if can_manage_policy_request:
                    extended_request.status = "approved"
                    log_data["admin_auto_approved"] = True
                    log.debug(log_data)
                    extended_request.reviewer = self.user
                    self_approval_comment = CommentModel(
                        id=str(uuid.uuid4()),
                        timestamp=int(time.time()),
                        user_email=self.user,
                        last_modified=int(time.time()),
                        text=f"Self-approved by admin: {self.user}",
                    )
                    extended_request.comments.append(self_approval_comment)

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
                        log_data["probe_auto_approved"] = True
                        log.debug(log_data)
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

            dynamo = UserDynamoHandler(self.user)
            request = await dynamo.write_policy_request_v2(extended_request)
            log_data["message"] = "New request created in Dynamo"
            log_data["request"] = request
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

        # TODO: slack message stuff
        self.write(response.json())


class RequestsHandler(BaseAPIV2Handler):
    """Handler for /api/v2/requests

    Allows read access to a list of requests. Returned requests are
    limited to what the requesting user has access to.
    """

    allowed_methods = ["GET", "POST"]

    async def get(self):
        """
        GET /api/v2/requests
        """
        tags = {
            "user": self.user,
        }
        stats.count("RequestsHandler.get", tags=tags)
        log_data = {
            "function": "RequestsHandler.get",
            "user": self.user,
            "message": "Writing all available requests",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Get requests")

    async def post(self):
        """
        POST /api/v2/requests
        """
        tags = {
            "user": self.user,
        }
        stats.count("RequestsHandler.post", tags=tags)
        log_data = {
            "function": "RequestsHandler.post",
            "user": self.user,
            "message": "Creating request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Create request")


class RequestDetailHandler(BaseAPIV2Handler):
    """Handler for /api/v2/requests/{request_id}

    Allows read and update access to a specific request.
    """

    allowed_methods = ["GET", "PUT"]

    async def get(self, request_id):
        """
        GET /api/v2/requests/{request_id}
        """
        tags = {
            "user": self.user,
        }
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
        tags = {
            "user": self.user,
        }
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

import sys

from pydantic import ValidationError

from consoleme.config import config
from consoleme.exceptions.exceptions import InvalidRequestParameter, MustBeFte
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.lib.dynamo import UserDynamoHandler
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.v2.requests import generate_request_from_change_model_array
from consoleme.models import RequestCreationModel

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()


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
            "admin_auto_approve" : "false" #TODO
        }

        Response example JSON: (Response Schema is ExtendedRequestModel in models.py)

        {
            "id": "223dd7c3-5f50-42dd-ad44-40cb60c9bb6b",
            "arn": "arn:aws:iam::123456789012:role/aRole",
            "timestamp": "2020-07-17T16:43:47+00:00",
            "justification": "Justification for making the request",
            "requester_email": "user@example.com",
            "approvers": [],
            "status": "pending",
            "changes": {
                "changes": [ <Change array from input> ]
            },
            "requester_info": {
                "email": "user@example.com",
                "extended_info": null,
                "details_url": null
            },
            "reviewer": null,
            "comments": [
                {
                    "id": "123",
                    "timestamp": "2020-07-17T16:43:47+00:00",
                    "edited": null,
                    "last_modified": null,
                    "user_email": "user2@example.com",
                    "user": null,
                    "text": "test comment"
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

        # TODO: auto-approval probes
        # TODO: admin self-approval stuff
        # TODO: update dynamo request based on auto-approval (if required)
        self.write(extended_request.json())


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

import sys
from typing import Any, Optional

import pkg_resources
import tornado.escape
import ujson as json
from tornado.template import Loader

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    NotAMemberException,
    PendingRequestAlreadyExists,
)
from consoleme.handlers.base import BaseHandler, BaseJSONHandler
from consoleme.lib.dynamo import UserDynamoHandler
from consoleme.lib.google import (
    add_user_to_group,
    raise_if_requires_bgcheck_and_no_bgcheck,
    remove_user_from_group,
)
from consoleme.lib.groups import (
    can_user_request_group_based_on_domain,
    does_group_require_bg_check,
    get_accessui_group_url,
    get_group_url,
)
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.requests import (
    can_approve_reject_request,
    can_cancel_request,
    can_move_back_to_pending,
    get_accessui_pending_requests_url,
    get_accessui_request_review_url,
    get_all_pending_requests,
    get_all_pending_requests_api,
    get_existing_pending_request,
    get_pending_requests_url,
    get_request_by_id,
    get_request_review_url,
)
from consoleme.lib.ses import (
    send_access_email_to_user,
    send_request_created_to_user,
    send_request_to_secondary_approvers,
)

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()
loader = Loader(pkg_resources.resource_filename("consoleme", "templates"))
aws = get_plugin_by_name(config.get("plugins.aws"))()
auth = get_plugin_by_name(config.get("plugins.auth"))()
group_mapping = get_plugin_by_name(config.get("plugins.group_mapping"))()


class RequestGroupHandler(BaseHandler):
    async def get_group_info_or_error(self, group: str) -> Optional[Any]:
        try:
            return await auth.get_group_info(group)
        except Exception as e:
            self.write(str(e))
            await self.finish()
            raise Exception(f"Unable to retrieve group info: {e}")

    async def return_error_if_user_in_group(self, group: str) -> None:
        """Determine if user is a member of group. If so, tell them so and give them opportunity to remove themselves."""
        if group in self.groups:
            self.write(
                "You are already in this group and are unable to request access. "
                "If desired, you may remove yourself from the main groups page."
            )
            await self.finish()
            raise Exception("User is already in group")

    async def return_error_if_group_not_requestable(
        self, group_info: Optional[Any]
    ) -> None:
        if not group_info.requestable:
            self.write(
                "You are unable to request access to this group because this group is not marked as requestable. "
                "If you believe this to be an error, please contact "
                "one of the following teams: {}".format(
                    ", ".join(config.get("groups.can_admin"))
                )
            )
            await self.finish()
            raise Exception("Group is not requestable")

    async def raise_if_user_already_has_pending_approved_request(
        self, group_info: Any
    ) -> None:
        # Determine if user already has a request. and tell them where to see it.
        existing_request = await get_existing_pending_request(self.user, group_info)
        if existing_request is not None:
            request_url = get_request_review_url(existing_request.get("request_id"))
            self.write(
                "You are unable to request access to {1} because you already have a pending or "
                "approved request for this group: "
                '<a href="{0}">{0}</a>'.format(request_url, group_info.get("name"))
            )
            await self.finish()
            raise Exception("Unable to request access to this group")

    async def raise_if_restricted(self, group_info: Any) -> None:
        if group_info.restricted:
            self.write(
                f"You are unable to request access to the {group_info.name} group because this group is marked "
                "as 'restricted'. This means that Consoleme will not be able to add users "
                "to this group due to its sensitivity. Please contact #nerds to request access."
            )
            await self.finish()
            raise Exception("Group is restricted")

    async def raise_if_user_is_not_in_correct_domain(
        self, user: str, group_info: Any
    ) -> None:
        if not can_user_request_group_based_on_domain(user, group_info):
            user_domain = user.split("@")[1]
            self.write(
                f"You are unable to request access to {group_info.name} because the group's domain is "
                f"{group_info.domain} and your domain is {user_domain}. This group is not configured to allow "
                f"cross domain users to request access to it yet. Please contact the owner of this group, "
                f"or #nerds if this group should be requestable by cross-domain users."
            )
            await self.finish()
            raise Exception("Unable to request access to this group")

    async def get(self, group: Optional[str] = None) -> None:
        """
        /accessui/request_access/(.*) - Renders request access to group page
        ---
        get:
            description: Renders page allowing users to request access to group
            responses:
                200:
                    description: Renders page
                403:
                    description: User has failed authn/authz.
        """
        function = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        if not group:
            self.write("You must pass an argument to this endpoint.")
            return

        if config.get("dynamic_config.accessui.deprecate") and not self.get_cookie(
            "bypass_accessui_deprecate"
        ):
            base_url = config.get("accessui_url")
            return self.redirect(f"{base_url}/groups/{group}", permanent=True)

        await self.authorization_flow(refresh_cache=True)
        stats.count(
            "requestgroup.get", tags={"user": self.user, "ip": self.ip, "group": group}
        )

        await self.return_error_if_user_in_group(group)
        group_info = await self.get_group_info_or_error(group)
        await self.return_error_if_group_not_requestable(group_info)
        await self.raise_if_user_already_has_pending_approved_request(group_info)
        await self.raise_if_user_is_not_in_correct_domain(self.user, group_info)
        await self.raise_if_restricted(group_info)

        log_data = {
            "user": self.user,
            "ip": self.ip,
            "function": function,
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }

        log.debug(log_data)
        await self.render(
            "requestgroup.html",
            page_title="ConsoleMe - Request Access to Group",
            current_page="groups",
            user=self.user,
            group=group_info,
            user_groups=self.groups,
            config=config,
            accessui_url=config.get("accessui_url"),
        )

    async def post(self, group: Optional[str] = None) -> None:
        """
        /accessui/request_access/(.*) - Requests access to a group
        ---
        post:
            description: Receives group access request and returns result
            responses:
                200:
                    description: Returns JSON result
                403:
                    description: User has failed authn/authz.
        """
        function = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        if not group:
            self.write("You must pass an argument to this endpoint.")
            return

        if not self.user:
            return

        log_data = {
            "user": self.user,
            "ip": self.ip,
            "function": function,
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }

        stats.count(
            "requestgroup.post", tags={"user": self.user, "ip": self.ip, "group": group}
        )

        await self.return_error_if_user_in_group(group)
        group_info = await self.get_group_info_or_error(group)
        await self.return_error_if_group_not_requestable(group_info)
        await self.raise_if_user_already_has_pending_approved_request(group_info)
        await self.raise_if_user_is_not_in_correct_domain(self.user, group_info)
        await self.raise_if_restricted(group_info)

        data = tornado.escape.json_decode(self.request.body)
        justification = None
        for item in data:
            if item.get("name") == "justification":
                justification = item.get("value")
                continue

        if not justification:
            self.write("No justification passed")
            await self.finish()
            raise Exception("No Justification passed for group request")

        await raise_if_requires_bgcheck_and_no_bgcheck(self.user, group_info)

        status = "pending"
        # Status is approved if there is no secondary approver for group
        if not group_info.secondary_approvers:
            status = "approved"

        # Status is approved if user is member of self approval group
        if group_info.self_approval_groups:
            for g in group_info.self_approval_groups:
                if g in self.groups:
                    status = "approved"

        dynamo_handler = UserDynamoHandler(self.user)
        try:
            request = dynamo_handler.add_request(
                self.user, group, justification, status=status, updated_by=self.user
            )
            self.request_id = request.get("request_id")
            if not self.request_id:
                raise Exception("Request {} does not have a request ID".format(request))
            log_data["request_id"] = self.request_id
            request_url = get_request_review_url(self.request_id)
            if status == "pending":
                if config.get("application_admin") in group_info.secondary_approvers:
                    user_info = await auth.get_user_info(self.user, object=True)
                    await aws.sns_publisher_group_requests(
                        self.user,
                        group,
                        justification,
                        self.request_id,
                        user_info.passed_background_check,
                    )
                await send_request_created_to_user(
                    self.user, group, self.user, status, request_url
                )
                if config.get("development"):
                    log_data[
                        "message"
                    ] = "Development mode: Not sending request to secondary approvers."
                    log.debug(log_data)
                else:
                    await send_request_to_secondary_approvers(
                        group_info.secondary_approvers,
                        group,
                        request_url,
                        pending_requests_url=get_pending_requests_url(),
                    )
            elif status == "approved":
                await add_user_to_group(self.user, group, self.user, request=request)
                await send_access_email_to_user(
                    self.user,
                    group,
                    self.user,
                    status,
                    request_url,
                    group_url=get_group_url(group),
                )
            else:
                raise Exception(f"Unknown request status: {request}", exc_info=True)

            result = {"status": "success"}

            if status == "pending":
                result["message"] = (
                    "Your request was succesfully submitted. "
                    "Please view your request here: {0}".format(request_url)
                )
                result["url"] = request_url
            elif status == "approved":
                result["message"] = (
                    "Your request has been approved and you have been added to the requested group. "
                    "Please wait up to 5 minutes for your group membership to propagate."
                )
            self.write(result)
            return
        except PendingRequestAlreadyExists:
            message = f"Error: A pending request already exists for user: {self.user} for group: {self.group}"
            log_data["error"] = message
            log.error(log_data)
            self.write(message)
            return


class ShowManageablePendingRequests(BaseHandler):
    """Shows all pending requests that user can manage by default."""

    async def get(self) -> None:
        """
        /accessui/pending/ - Renders page with pending requests view.
        ---
        get:
            description: Renders page with list of pending requests
            responses:
                200:
                    description: Renders pending requests view
                403:
                    description: User has failed authn/authz.
        """

        if not self.user:
            return
        pending_requests = await get_all_pending_requests(self.user, self.groups)

        group_column_header = "Group or ARN"

        await self.render(
            "pending_requests.html",
            page_title="ConsoleMe - Pending Requests",
            current_page="pending",
            user=self.user,
            pending_requests=pending_requests,
            user_groups=self.groups,
            config=config,
            group_column_header=group_column_header,
            accessui_url=config.get("accessui_url"),
        )


class JSONBaseRequestHandler(BaseJSONHandler):
    async def get(self):
        """
        /api/v1/requests - Retrieves pending group access requests
        ---
        get:
            description: Retrieves pending group access requests and returns list
            responses:
                200:
                    description: Returns JSON request list
        """
        requests = await get_all_pending_requests_api(self.user)
        await self.finish(json.dumps(requests))

    async def post(self):
        """
        /api/v1/requests - Receives group access requests
        ---
        post:
            description: Receives group access request and returns result
            responses:
                200:
                    description: Returns JSON request object
                422:
                    description: Missing parameter
                403:
                    description: User has failed authn/authz.
                404:
                    description: Unable to find the specified group
        """
        log_data = {
            "-----------------------------": "-----------------------------",
            "function": "JSONBaseRequestHandler.post",
        }

        data = tornado.escape.json_decode(self.request.body)
        justification = data.get("justification", None)
        log_data["justification"] = justification
        group = data.get("group", None)
        log_data["group"] = group

        if justification is None or group is None:
            log_data[
                "error"
            ] = "A requested group and justification must be passed to this endpoint."
            log.error(log_data)
            self.send_error(422, message=log_data["error"])
            return

        try:
            group_info = await auth.get_group_info(group)
        except Exception as e:
            log_data["error"] = e
            log.error(log_data)
            self.send_error(
                404, message=f"Unable to retrieve the specified group {group}: {e}"
            )
            return

        user_info = await auth.get_user_info(self.user, object=True)
        user_groups = await auth.get_groups(self.user)
        existing_request = await get_existing_pending_request(self.user, group_info)

        auth_error = None
        if group in user_groups:
            auth_error = (
                "You are already in this group and are unable to request access."
            )
        elif existing_request is not None:
            auth_error = (
                f"You already have a pending or approved request for this group. "
                f"Request id: {existing_request.get('request_id')}"
            )
        elif not group_info.requestable:
            auth_error = "This group is not requestable."
        elif group_info.restricted:
            auth_error = "This group is marked as 'restricted'."
        elif not can_user_request_group_based_on_domain(self.user, group_info):
            auth_error = "You are not in this group's domain and the group does not allow cross domain membership."
        elif (
            does_group_require_bg_check(group_info)
            and not user_info.passed_background_check
        ):
            auth_error = (
                f"User {self.user} has not passed background check. Group {group_info.name} "
                f"requires a background check. Please contact Nerds"
            )

        if auth_error is not None:
            log_data["error"] = auth_error
            log.error(log_data)
            self.send_error(403, message=auth_error)
            return

        status = "pending"
        # Status is approved if there is no secondary approver for group
        if not group_info.secondary_approvers:
            status = "approved"

        user_groups_including_indirect = await auth.get_groups(
            self.user, only_direct=False
        )
        # Status is approved if approver list includes user or group in user membership
        for g in group_info.secondary_approvers:
            if g in user_groups_including_indirect or g == self.user:
                status = "approved"

        # Status is approved if user is member of self approval group
        if group_info.self_approval_groups:
            for g in group_info.self_approval_groups:
                if g in user_groups:
                    status = "approved"

        try:
            dynamo_handler = UserDynamoHandler(self.user)
            request = dynamo_handler.add_request(
                self.user, group, justification, status=status, updated_by=self.user
            )
            request_id = request.get("request_id")

            if not request_id:
                raise Exception(f"Request {request} does not have a request ID")

            log_data["request_id"] = request_id
            request_url = get_accessui_request_review_url(request_id)

            if status == "pending":
                if config.get("application_admin") in group_info.secondary_approvers:
                    await aws.sns_publisher_group_requests(
                        self.user,
                        group,
                        justification,
                        request_id,
                        user_info.passed_background_check,
                    )

                await send_request_created_to_user(
                    self.user,
                    group,
                    self.user,
                    status,
                    request_url,
                    sending_app="accessui",
                )

                if config.get("development"):
                    log_data[
                        "message"
                    ] = "Development mode: Not sending request to secondary approvers."
                    log.debug(log_data)
                else:
                    await send_request_to_secondary_approvers(
                        group_info.secondary_approvers,
                        group,
                        request_url,
                        pending_requests_url=get_accessui_pending_requests_url(),
                        sending_app="accessui",
                    )

            elif status == "approved":
                await add_user_to_group(self.user, group, self.user, request=request)
                await send_access_email_to_user(
                    self.user,
                    group,
                    self.user,
                    status,
                    request_url,
                    group_url=get_accessui_group_url(group),
                    sending_app="accessui",
                )
            else:
                raise Exception(f"Unknown request status: {request}", exc_info=True)

            await self.finish(json.dumps(request))
            return
        except PendingRequestAlreadyExists:
            auth_error = f"Error: A pending request already exists for user: {self.user} for group: {group}"
            log_data["error"] = auth_error
            log.error(log_data)
            self.send_error(403, message=auth_error)
            return


class JSONRequestHandler(BaseJSONHandler):
    async def get(self, request_id=None):
        """
        /api/v1/requests/(.*) - Retrieves a group access request matching the given id
        ---
        get:
            description: Retrieves a group access request matching the given id and returns object
            responses:
                200:
                    description: Returns JSON request object
                404:
                    description: No matching request found
        """
        if not request_id:
            raise Exception("request_id must be passed to this endpoint.")

        request = await get_request_by_id(self.user, request_id)

        if request is None:
            self.send_error(404, message=f"Request {request_id} not found.")
        else:
            await self.finish(json.dumps(request))

    async def put(self, request_id=None):
        """
        /api/v1/requests/(.*) - Receives group access request modifications
        ---
        put:
            description: Receives group access request modification and returns result
            responses:
                200:
                    description: Returns JSON request object
                422:
                    description: Missing required parameter
                403:
                    description: User has failed authn/authz.
        """
        if not request_id:
            raise Exception("request_id must be passed to this endpoint.")

        log_data = {"function": "JSONRequestHandler.put", "request_id": request_id}

        data = tornado.escape.json_decode(self.request.body)
        reviewer_comments = data.get("comment", None)
        new_status = data.get("status", None)

        user_groups_including_indirect = await auth.get_groups(
            self.user, only_direct=False
        )
        request = await get_request_by_id(self.user, request_id)
        secondary_approvers = await auth.get_secondary_approvers(request["group"])

        can_approve_reject = False
        can_cancel = False
        can_change_to_pending = False
        if request.get("status") in ["pending", "approved"]:
            can_approve_reject = await can_approve_reject_request(
                self.user, secondary_approvers, user_groups_including_indirect
            )
            can_cancel = await can_cancel_request(
                self.user, request["username"], user_groups_including_indirect
            )

        if request.get("status") in ["cancelled", "rejected"]:
            can_change_to_pending = await can_move_back_to_pending(
                self.user, request, user_groups_including_indirect
            )

        log_data["status"] = new_status
        log_data["user"] = self.user
        log_data["requestor"] = request.get("username")

        if not new_status:
            log_data["error"] = "Please pass a new status"
            log.error(log_data)
            self.send_error(422, message=log_data["error"])
            return

        auth_error = None
        if not can_approve_reject and not can_cancel and not can_change_to_pending:
            auth_error = "You are unauthorized to change the status on this request."
        elif new_status == "cancelled" and not can_cancel:
            auth_error = "You are unauthorized to cancel this request."
        elif new_status in ["approved", "rejected"] and not can_approve_reject:
            auth_error = "You are unauthorized to approve or reject this request."
        elif new_status == "pending" and not can_change_to_pending:
            auth_error = "You are unauthorized to make this request pending."

        if auth_error is not None:
            log_data["error"] = auth_error
            log.error(log_data)
            self.send_error(403, message=auth_error)
            return

        log_data["updated_by"] = self.user
        log.debug(log_data)
        dynamo_handler = UserDynamoHandler(self.user)
        request = dynamo_handler.change_request_status_by_id(
            request_id, new_status, self.user, reviewer_comments=reviewer_comments
        )
        status = request.get("status")
        requesting_user = request.get("username")
        group = request.get("group")
        if status == "approved":
            await add_user_to_group(requesting_user, group, self.user, request=request)
        elif status in ["cancelled", "rejected"]:
            try:
                await remove_user_from_group(requesting_user, group, self.user)
            except NotAMemberException:
                # User has already been removed from the group. Swallow this exception.
                pass

        request_url = get_accessui_request_review_url(request.get("request_id"))
        await send_access_email_to_user(
            requesting_user,
            group,
            self.user,
            status,
            request_url,
            reviewer_comments=reviewer_comments,
            group_url=get_accessui_group_url(group),
            sending_app="accessui",
        )

        decorated_request = await get_request_by_id(self.user, request_id)
        await self.finish(json.dumps(decorated_request))

import asyncio
import sys
from typing import Optional

import pkg_resources
import tornado.escape
import ujson as json
from asgiref.sync import sync_to_async
from googleapiclient.errors import HttpError
from tornado.escape import xhtml_escape
from tornado.template import Loader
from validate_email import validate_email

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    BackgroundCheckNotPassedException,
    BulkAddPrevented,
    DifferentUserGroupDomainException,
    NotAMemberException,
    UnableToEditSensitiveAttributes,
    UnableToModifyRestrictedGroupMembers,
    UserAlreadyAMemberOfGroupException,
)
from consoleme.handlers.base import BaseHandler, BaseJSONHandler
from consoleme.lib.auth import (
    can_edit_attributes,
    can_edit_sensitive_attributes,
    can_modify_members,
    is_sensitive_attr,
)
from consoleme.lib.dynamo import UserDynamoHandler
from consoleme.lib.generic import auto_split, generate_html, regex_filter, str2bool
from consoleme.lib.google import (
    add_user_to_group,
    add_user_to_group_task,
    api_add_user_to_group_or_raise,
    remove_user_from_group,
    remove_user_from_group_task,
)
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.timeout import Timeout

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()
loader = Loader(pkg_resources.resource_filename("consoleme", "templates"))
aws = get_plugin_by_name(config.get("plugins.aws"))()
auth = get_plugin_by_name(config.get("plugins.auth"))()
group_mapping = get_plugin_by_name(config.get("plugins.group_mapping"))()


class GroupsHandler(BaseHandler):
    async def get(self) -> None:
        """
        /accessui/groups/ - User endpoint used to render page that will list all groups in tabular format.
        ---
        post:
            description: Renders page that will make XHR request to get group information
            responses:
                200:
                    description: Renders page that will make subsequent XHR requests
                403:
                    description: User has failed authn/authz.
        """

        if config.get("dynamic_config.accessui.deprecate") and not self.get_cookie(
            "bypass_accessui_deprecate"
        ):
            base_url = config.get("accessui_url")
            return self.redirect(f"{base_url}/groups", permanent=True)

        if not self.user:
            return

        requestable = self.get_argument("requestable", False)
        stats.count(
            "groups.get",
            tags={"user": self.user, "ip": self.ip, "requestable": requestable},
        )

        log_data = {
            "user": self.user,
            "ip": self.ip,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "requestable": requestable,
        }

        log.debug(log_data)

        current_page = "groups"
        page_title = "ConsoleMe - Your Groups"
        if requestable:
            current_page = "accessui"
            page_title = "ConsoleMe - Access Requests"

        await self.render(
            "groups.html",
            page_title=page_title,
            current_page=current_page,
            user=self.user,
            user_groups=self.groups,
            config=config,
            accessui_url=config.get("accessui_url"),
        )


class GroupHandler(BaseHandler):
    async def get(self, group: Optional[str] = None) -> None:
        """
        /accessui/group/(.*) - Renders page that will show information about a group, including attributes and members.
        ---
        get:
            description: Renders group information page.
            responses:
                200:
                    description: Returns page
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

        if not self.user:
            return

        stats.count(
            "group.get", tags={"user": self.user, "ip": self.ip, "group": group}
        )

        try:
            group_info = await auth.get_group_info(group)
        except Exception as e:
            self.write(str(e))
            await self.finish()
            return

        can_edit = can_edit_attributes(self.user, self.groups, group_info)
        can_add_remove_members = can_modify_members(self.user, self.groups, group_info)
        can_edit_sensitive_attrs = can_edit_sensitive_attributes(
            self.user, self.groups, group_info
        )

        log_data = {
            "user": self.user,
            "ip": self.ip,
            "group": group,
            "function": function,
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "can_edit": can_edit,
            "can_add_remove_members": can_add_remove_members,
        }

        log.debug(log_data)
        await self.render(
            "group.html",
            page_title=f"ConsoleMe - {group_info.name} info",
            current_page="groups",
            user=self.user,
            group=group_info,
            can_edit=can_edit,
            can_modify_members=can_add_remove_members,
            can_edit_sensitive_attrs=can_edit_sensitive_attrs,
            request_url=f"{config.get('url')}/accessui/request_access/{group_info.name}",
            config=config,
            user_groups=self.groups,
            accessui_url=config.get("accessui_url"),
        )

    async def write_error(self, error):
        self.write({"status": "error", "message": error})
        await self.finish()
        raise Exception(error)

    async def post(self, group: Optional[str] = None) -> None:
        """
        /accessui/group/(.*) - Update group attributes or members
        ---
        post:
            description: Updates group information and returns status
            responses:
                200:
                    description: Renders page
                403:
                    description: User has failed authn/authz.
        """
        function = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )

        error = None

        if not group:
            self.write("You must pass an argument to this endpoint.")
            return

        if not self.user:
            return

        data_list = tornado.escape.json_decode(self.request.body)
        data = {}
        for item in data_list:
            data[item.get("name")] = item.get("value")

        try:
            group_info = await auth.get_group_info(group, members=False)
        except Exception as e:
            self.write(str(e))
            await self.finish()
            return

        can_edit = can_edit_attributes(self.user, self.groups, group_info)
        can_add_remove_members = can_modify_members(self.user, self.groups, group_info)
        can_edit_sensitive_attrs = can_edit_sensitive_attributes(
            self.user, self.groups, group_info
        )

        log_data = {
            "user": self.user,
            "ip": self.ip,
            "group": group,
            "function": function,
            "message": "Incoming request",
            "data": data,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "can_edit": can_edit,
            "can_modify_members": can_add_remove_members,
            "can_edit_sensitive_attrs": can_edit_sensitive_attrs,
        }

        list_attributes = config.get("groups.attributes.list", [])
        bool_attributes = config.get("groups.attributes.boolean", [])

        modifications = dict()
        # Configure boolean values for certain attributes if they are sent in the POST request

        for b in bool_attributes:
            boolean = b.get("name")
            if data.get(boolean):
                if data.get(boolean, "") == "on":
                    modifications[boolean] = True
                elif data.get(boolean, "") == "off":
                    modifications[boolean] = False

        # Configure string values for certain attributes if they are sent in the POST request
        for l in list_attributes:
            var = l.get("name")
            if data.get(var):
                modifications[var] = data[var]

        add_members = []
        if data.get("add_members"):
            add_members = auto_split(data.get("add_members"))
        remove_members = []
        if data.get("remove_members"):
            remove_members = auto_split(data.get("remove_members"))
        log_data["modifications"] = modifications
        log_data["add_members"] = add_members
        log_data["remove_members"] = remove_members
        log.info(log_data)
        results = []

        if (add_members or remove_members) and not can_add_remove_members:
            await self.write_error("Unauthorized to modify members")
            return

        error = False

        if add_members and remove_members:
            await self.write_error(
                "You are trying to add and remove members in the same request. "
                "Please make two separate requests for this."
            )

        tasks = []

        if add_members:
            for member in add_members:
                task = asyncio.ensure_future(
                    add_user_to_group_task(member, group, self.user, self.groups)
                )
                tasks.append(task)

        if remove_members:
            for member in remove_members:
                task = asyncio.ensure_future(
                    remove_user_from_group_task(member, group, self.user, self.groups)
                )
                tasks.append(task)
        responses = asyncio.gather(*tasks)
        results = await responses

        for r in results:
            if r["Error"] is True:
                error = "There was at least one problem."

        for attr in list_attributes:
            s = attr.get("name")
            if modifications.get(s):
                for u in modifications.get(s).split(","):
                    u = u.strip()
                    if not validate_email(u):
                        await self.write_error(f"Invalid e-mail address entered: {u}")
                        return

        if not can_edit:
            await self.write_error("Unauthorized to edit this group.")
            return

        try:
            group_info = await auth.get_group_info(group, members=False)
        except Exception as e:
            await self.write_error(str(e))
            await self.finish()
            return

        for k, v in modifications.items():
            if type(v) == bool and v == str2bool(group_info.get(k)):
                # Types are stored as a string.
                # Here, we skip modifying a group attribute if an attribute already equals True/False and the
                # attribute is the equivalent: "true"/"false"
                continue
            elif (
                k in list_attributes
                and v is not None
                and v.split(",") == group_info.get(k)
            ):
                # secondary approvers is a list. We convert user input to a list prior to the comparison.
                continue
            elif v == group_info.get(k):
                # If the string value of the modification is the same as what we already have, don't modify
                # the attribute.
                continue
            # Check for sensitive attribute here and 'can_edit_sensitive_attrs'
            if (
                is_sensitive_attr(k)
                or group_info.restricted
                or group_info.compliance_restricted
            ) and not can_edit_sensitive_attrs:
                raise UnableToEditSensitiveAttributes(
                    f"You are not authorized to edit sensitive attribute: {k}"
                )
            await auth.put_group_attribute(group, k, v)
        html = generate_html(results)

        if not error:
            success_response = (
                "Success. Please wait up to 5 minutes for your changes to propagate and be reflected "
                "on this page."
            )
            self.write({"status": "success", "message": success_response, "html": html})
        else:
            self.write({"status": "error", "message": error, "html": html})
        await self.finish()


class GetGroupsHandler(BaseHandler):
    """Endpoint for parsing group information."""

    async def get(self) -> None:
        """/accessui/get_groups/ - Filters and returns cached group information from Redis.
        ---
        post:
            description: Returns group information
            responses:
                200:
                    description: returns JSON with filtered group information.
                403:
                    description: User has failed authn/authz.
        """

        if not self.user:
            return
        draw = int(self.request.arguments.get("draw")[0])
        length = int(self.request.arguments.get("length")[0])
        start = int(self.request.arguments.get("start")[0])
        finish = start + length
        group_name_search = self.request.arguments.get("columns[0][search][value]")[
            0
        ].decode("utf-8")
        group_description_search = self.request.arguments.get(
            "columns[1][search][value]"
        )[0].decode("utf-8")
        group_status_search = self.request.arguments.get("columns[2][search][value]")[
            0
        ].decode("utf-8")
        groups = await auth.get_cached_groups()
        requestable_groups = await auth.get_all_requestable_groups()

        if group_status_search == "member":
            groups = [g for g in groups if g.get("name") in self.groups]
        if group_status_search == "not_member":
            groups = [g for g in groups if g.get("name") not in self.groups]
        if group_status_search == "requestable":
            groups = [g for g in groups if g.get("name") in requestable_groups]

        data = []
        filters = [
            {"field": "name", "filter": group_name_search},
            {"field": "description", "filter": group_description_search},
        ]

        results = groups

        try:
            with Timeout(seconds=5):
                for f in filters:
                    results = await sync_to_async(regex_filter)(f, results)
        except TimeoutError:
            self.write("Query took too long to run. Check your filter.")
            await self.finish()
            raise
        dynamo_handler = UserDynamoHandler(self.user)
        existing_requests = dynamo_handler.get_requests_by_user(
            self.user, use_cache=True
        )
        pending_requests = {}

        # Get existing requests from Redis cache, if possible. Otherwise, get them directly from DDB

        if existing_requests:
            for request in existing_requests:
                if request.get("status", "") == "pending":
                    pending_requests[request.get("group")] = request.get("request_id")

        for group in results[start:finish]:
            # If member, show a link that lets them remove their access
            # If unrequestable and not member, show Unrequestable
            # If requestable and not member, show request access link
            # If user has a pending request, link to the request
            member = True if group.get("name") in self.groups else False
            if member:
                action = "Member"
            elif pending_requests.get(group.get("name")):
                request_url = f"/accessui/request/{xhtml_escape(pending_requests.get(group.get('name')))}"
                action = f'<a target="_blank" href="{request_url}">Pending Request</a>'

            elif group.get("name") in requestable_groups:
                request_url = (
                    f"/accessui/request_access/{xhtml_escape(group.get('name'))}"
                )
                action = f'<a target="_blank" href="{request_url}">Request Access</a>'
            else:
                action = "Not requestable"
            data.append(
                [
                    xhtml_escape(group.get("name")),
                    xhtml_escape(group.get("description")),
                    action,
                ]
            )
            if len(data) == length:
                break

        response = {
            "draw": draw,
            "recordsTotal": len(groups),
            "recordsFiltered": len(results),
            "data": data,
        }
        self.write(response)
        await self.finish()


class JSONGroupHandler(BaseJSONHandler):
    async def patch(self, group_name=None):
        """
        /api/v1/groups/([a-zA-Z0-9_-]+)/ - Modifies a groups extended attributes used by access ui
        ---
        patch:
            description: Modify a groups extended attributes
            responses:
                204:
                    description: The group was successfully modified
                400:
                    description: An invalid email was sent for a list attribute
                403:
                    description: Unable to modify group properties due to restriction
                404:
                    description: Unable to retrieve the specified group
        """
        if group_name is None:
            raise Exception("group_name must be passed to this endpoint.")

        function = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        stats.count(function, tags={"group_name": group_name, "caller": self.user})

        data = tornado.escape.json_decode(self.request.body)
        log_data = {
            "function": function,
            "group_name": group_name,
            "caller": self.user,
            "data": data,
        }

        try:
            group_info = await auth.get_group_info(group_name)
        except Exception as e:
            log_data["error"] = e
            log.error(log_data)
            self.send_error(
                404, message=f"Unable to retrieve the specified group: {group_name}"
            )
            return

        user_groups = await auth.get_groups(self.user)
        can_edit = can_edit_attributes(self.user, user_groups, group_info)
        can_edit_sensitive_attrs = can_edit_sensitive_attributes(
            self.user, user_groups, group_info
        )
        list_attributes = config.get("groups.attributes.list", [])
        bool_attributes = config.get("groups.attributes.boolean", [])

        log_data["can_edit"] = can_edit
        log_data["can_edit_sensitive_attrs"] = can_edit_sensitive_attrs

        if not can_edit:
            log_data["error"] = "Unauthorized to edit this group."
            log.error(log_data)
            self.send_error(403, message=log_data["error"])
            return

        for attr in bool_attributes:
            name = attr.get("name")
            value = data.get(name)
            if value and value != "false" and value != "true":
                log_data["error"] = f"Invalid boolean value entered for {name}: {value}"
                log.error(log_data)
                self.send_error(400, message=log_data["error"])
                return

        for attr in list_attributes:
            name = attr.get("name")
            value = data.get(name)
            if value:
                for u in value.split(","):
                    u = u.strip()
                    if not validate_email(u):
                        log_data["error"] = f"Invalid e-mail address entered: {u}"
                        log.error(log_data)
                        self.send_error(400, message=log_data["error"])
                        return

        # Do good bits here
        for k, v in data.items():
            if v == group_info.get(k):
                # If the string value of the modification is the same as what we have in our attribute store,
                # don't modify the attribute.
                continue
            # Check for sensitive attribute here and 'can_edit_sensitive_attrs'
            if (
                is_sensitive_attr(k)
                or group_info.restricted
                or group_info.compliance_restricted
            ) and not can_edit_sensitive_attrs:
                log_data[
                    "error"
                ] = f"You are not authorized to edit sensitive attribute: {k}"
                log.error(log_data)
                self.send_error(403, message=log_data["error"])
                return

        await auth.put_group_attributes(group_name, data.items())

        log_data["message"] = "Success"
        log.debug(log_data)
        self.set_status(204)
        await self.finish()


class JSONBulkGroupMemberHandler(BaseJSONHandler):
    async def post(self, group_name=None):
        """
        /api/v1/groups/([a-zA-Z0-9_-]+)/members - Adds members to a given group
        ---
        post:
            description: Adds a given list of users to a given group
            responses:
                200:
                    description: The request was successfully recieved. The outcome of each add will be returned in the request response.
        """
        user_list = tornado.escape.json_decode(self.request.body)
        if group_name is None or not user_list:
            raise Exception(
                "group_name and a list of users must be passed to this endpoint."
            )

        function = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        stats.count(
            function,
            tags={
                "group_name": group_name,
                "user_list": user_list,
                "caller": self.user,
            },
        )

        log_data = {
            "function": function,
            "group_name": group_name,
            "user_list": user_list,
        }

        tasks = []
        for member_name in user_list:
            task = api_add_user_to_group_or_raise(
                group_name, member_name, actor=self.user
            )
            tasks.append(task)

        responses = asyncio.gather(*tasks, return_exceptions=True)
        data = await responses

        results = []
        for index, status in enumerate(data):
            member_name = user_list[index]

            if status == "ADDED" or status == "REQUESTED":
                message = (
                    f"{member_name} added to {group_name}"
                    if status == "ADDED"
                    else f"{group_name} requested for {member_name}"
                )
                result = {
                    "success": True,
                    "status": status,
                    "message": message,
                    "member": member_name,
                    "group": group_name,
                }
            else:
                result = {
                    "success": False,
                    "status": "FAILED",
                    "message": str(status),
                    "member": member_name,
                    "group": group_name,
                }
            results.append(result)

        log.debug(log_data)
        self.write(json.dumps(results))
        self.set_header("Content-Type", "application/json")
        await self.finish()


class JSONGroupMemberHandler(BaseJSONHandler):
    async def post(self, group_name=None, member_name=None):
        """
        /api/v1/groups/([a-zA-Z0-9_-]+)/members/([a-zA-Z0-9_-]+) - Adds member to a given group
        ---
        post:
            description: Adds a given user to a given group
            responses:
                200:
                    description: Member was successfully added to the group
                403:
                    description: Unable to add member due to restriction
        """
        if group_name is None or member_name is None:
            raise Exception(
                "group_name and member_name must be passed to this endpoint."
            )

        function = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        stats.count(
            function,
            tags={
                "group_name": group_name,
                "member_name": member_name,
                "caller": self.user,
            },
        )

        log_data = {
            "function": function,
            "group_name": group_name,
            "member_name": member_name,
        }

        try:
            group_info = await auth.get_group_info(group_name)
        except Exception as e:
            log_data["error"] = e
            log.error(log_data)
            self.send_error(404, message=f"Unable to retrieve the specified group: {e}")
            return

        user_groups = await auth.get_groups(self.user)
        can_add_remove_members = can_modify_members(self.user, user_groups, group_info)

        if not can_add_remove_members:
            log_data["error"] = "Unauthorized to modify members of this group."
            log.error(log_data)
            self.send_error(403, message=log_data["error"])
            return

        auth_error = None
        try:
            await add_user_to_group(member_name, group_name, self.user)
        except BackgroundCheckNotPassedException as e:
            auth_error = e.msg
        except DifferentUserGroupDomainException as e:
            auth_error = e.msg
        except UnableToModifyRestrictedGroupMembers as e:
            auth_error = e.msg
        except BulkAddPrevented as e:
            auth_error = e.msg
        except HttpError as e:
            # Inconsistent GG API error - ignore failure for user already existing
            if e.resp.reason == "duplicate":
                pass
        except UserAlreadyAMemberOfGroupException:
            pass

        if auth_error is not None:
            log_data["error"] = auth_error
            log.error(log_data)
            self.send_error(403, message=auth_error)
            return

        log_data["message"] = "Success"
        log.debug(log_data)
        self.set_status(204)
        await self.finish()

    async def delete(self, group_name=None, member_name=None):
        """
        /api/v1/groups/([a-zA-Z0-9_-]+)/members/([a-zA-Z0-9_-]+) - Removes member from a given group
        ---
        delete:
            description: Removes a given user from a given group
            responses:
                204:
                    description: Member was successfully removed or the member or group is already not a member
                403:
                    description: Unable to remove member due to restriction
        """
        if group_name is None or member_name is None:
            raise Exception(
                "group_name and member_name must be passed to this endpoint."
            )

        function = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        stats.count(
            function,
            tags={
                "group_name": group_name,
                "member_name": member_name,
                "caller": self.user,
            },
        )

        log_data = {
            "function": function,
            "group_name": group_name,
            "member_name": member_name,
        }

        try:
            await remove_user_from_group(member_name, group_name, self.user)
        except UnableToModifyRestrictedGroupMembers as e:
            log_data["error"] = e.msg
            log.error(log_data)
            self.send_error(403, message=e.msg)
            return
        except NotAMemberException:
            pass

        log_data["message"] = "Success"
        log.debug(log_data)
        self.set_status(204)
        await self.finish()

import asyncio
import json
import sys
from typing import Optional

import pkg_resources
import tornado.escape
from tornado.template import Loader

from consoleme.config import config
from consoleme.handlers.base import BaseHandler, BaseJSONHandler
from consoleme.lib.auth import can_modify_members
from consoleme.lib.generic import auto_split, generate_html, regex_filter
from consoleme.lib.google import (
    add_user_to_group_task,
    api_add_user_to_group_or_raise,
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


class UsersHandler(BaseHandler):
    async def get(self) -> None:
        """
        /accessui/users/ - Renders table that will make subsequent XHR requests to retrieve list of users.
        ---
        get:
            description: Renders users.html
            responses:
                200:
                    description: renders users.html
                403:
                    description: User has failed authn/authz.
        """

        if config.get("dynamic_config.accessui.deprecate") and not self.get_cookie(
            "bypass_accessui_deprecate"
        ):
            base_url = config.get("accessui_url")
            return self.redirect(f"{base_url}/users", permanent=True)

        if not self.user:
            return
        stats.count("users.get", tags={"user": self.user, "ip": self.ip})

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
            "users.html",
            page_title="ConsoleMe - Users",
            current_page="users",
            user=self.user,
            user_groups=self.groups,
            config=config,
            accessui_url=config.get("accessui_url"),
        )


class UserHandler(BaseHandler):
    """
    /accessui/user/(.*) - Renders page with user and specific user attributes
    ---
    get:
        description: Renders user.html with populated user info
        responses:
            200:
                description: renders user.html
            403:
                description: User has failed authn/authz.
    """

    async def get(self, user: str) -> None:
        function = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        if not user:
            self.write("You must pass an argument to this endpoint.")
            return

        if config.get("dynamic_config.accessui.deprecate") and not self.get_cookie(
            "bypass_accessui_deprecate"
        ):
            base_url = config.get("accessui_url")
            return self.redirect(f"{base_url}/users/{user}", permanent=True)

        if not self.user:
            return

        stats.count(
            "user.get", tags={"user": self.user, "ip": self.ip, "requested_user": user}
        )

        can_add_remove_members = can_modify_members(self.user, self.groups, None)

        log_data = {
            "user": self.user,
            "ip": self.ip,
            "requested_user": user,
            "function": function,
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "can_add_remove_members": can_add_remove_members,
        }

        try:
            user_info = await auth.get_user_info(user)
            user_groups = await auth.get_group_memberships(
                user, scopes=[user.split("@")[1]]
            )
        except Exception as e:
            self.write(str(e))
            await self.finish()
            return

        log.debug(log_data)
        await self.render(
            "user.html",
            page_title=f"ConsoleMe - {user} info",
            current_page="users",
            user=self.user,
            user_info=user_info,
            affected_user_groups=user_groups,
            can_modify_members=can_add_remove_members,
            config=config,
            user_groups=self.groups,
            accessui_url=config.get("accessui_url"),
        )

    async def write_error(self, error):
        self.write({"status": "error", "message": error})
        await self.finish()
        raise Exception(error)

    async def post(self, user: Optional[str] = None):
        """
        /accessui/user/(.*) - Update user attributes
        ---
        post:
            description: Returns JSON with request status
            responses:
                200:
                    description: JSON with updated user attributes
                403:
                    description: User has failed authn/authz.
        """
        function = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )

        error = None

        if not user:
            self.write("You must pass an argument to this endpoint.")
            return

        if not self.user:
            return

        stats.count(
            "user.post", tags={"user": self.user, "ip": self.ip, "requested_user": user}
        )

        data_list = tornado.escape.json_decode(self.request.body)
        data = {}
        for item in data_list:
            data[item.get("name")] = item.get("value")
        can_add_remove_members = can_modify_members(self.user, self.groups, None)

        log_data = {
            "user": self.user,
            "ip": self.ip,
            "affected_user": user,
            "function": function,
            "message": "Incoming request",
            "data": data,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "can_modify_members": can_add_remove_members,
        }

        add_groups = []
        if data.get("add_groups"):
            add_groups = auto_split(data.get("add_groups"))
        remove_groups = []
        if data.get("remove_groups"):
            remove_groups = auto_split(data.get("remove_groups"))
        log_data["add_groups"] = add_groups
        log_data["remove_groups"] = remove_groups
        log.info(log_data)

        if add_groups and remove_groups:
            await self.write_error(
                "You are trying to add and remove groups in the same request. "
                "Please make two separate requests for this."
            )

        tasks = []

        if add_groups:
            for group in add_groups:
                task = asyncio.ensure_future(
                    add_user_to_group_task(user, group, self.user, self.groups)
                )
                tasks.append(task)

        if remove_groups:
            for group in remove_groups:
                task = asyncio.ensure_future(
                    remove_user_from_group_task(user, group, self.user, self.groups)
                )
                tasks.append(task)
        responses = asyncio.gather(*tasks)
        results = await responses

        for r in results:
            if r["Error"] is True:
                error = "There was at least one problem."

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


class GetUsersHandler(BaseHandler):
    """Endpoint for parsing user information."""

    async def get(self) -> None:
        """
        /accessui/get_users/ - Filters and returns cached user information from Redis.
        ---
        get:
            description: Returns user information
            responses:
                200:
                    description: returns JSON with filtered user information.
                403:
                    description: User has failed authn/authz.
        """

        if not self.user:
            return
        draw = int(self.request.arguments.get("draw")[0])
        length = int(self.request.arguments.get("length")[0])
        start = int(self.request.arguments.get("start")[0])
        finish = start + length
        user_fullname_search = self.request.arguments.get("columns[0][search][value]")[
            0
        ].decode("utf-8")
        user_username_search = self.request.arguments.get("columns[1][search][value]")[
            0
        ].decode("utf-8")
        user_status = self.request.arguments.get("columns[2][search][value]")[0].decode(
            "utf-8"
        )
        users = await auth.get_cached_users()

        data = []
        filters = [
            {"field": "fullname", "filter": user_fullname_search},
            {"field": "username", "filter": user_username_search},
            {"field": "status", "filter": user_status},
        ]

        results = users

        try:
            with Timeout(seconds=5):
                for f in filters:
                    results = regex_filter(f, results)
        except TimeoutError:
            self.write("Query took too long to run. Check your filter.")
            await self.finish()
            raise

        for user in results[start:finish]:
            fullname = user.get("fullname")
            data.append(
                [
                    tornado.escape.xhtml_escape(fullname),
                    tornado.escape.xhtml_escape(user.get("username")),
                    tornado.escape.xhtml_escape(user.get("status")),
                ]
            )
            if len(data) == length:
                break

        response = {
            "draw": draw,
            "recordsTotal": len(users),
            "recordsFiltered": len(results),
            "data": data,
        }
        self.write(response)
        await self.finish()


class JSONBulkUserMembershipHandler(BaseJSONHandler):
    async def post(self, member_name=None):
        """
        /api/v1/users/([a-zA-Z0-9_-]+)/memberships - Adds member to a given groups
        ---
        post:
            description: Adds a user to a given list of groups
            responses:
                200:
                    description: The request was successfully recieved. The outcome of each add will be returned in the request response.
        """
        group_list = tornado.escape.json_decode(self.request.body)
        if member_name is None or not group_list:
            raise Exception(
                "member_name and a list of groups must be passed to this endpoint."
            )

        function = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        stats.count(
            function,
            tags={
                "member_name": member_name,
                "group_list": group_list,
                "caller": self.user,
            },
        )

        log_data = {
            "function": function,
            "member_name": member_name,
            "group_list": group_list,
        }

        tasks = []
        for group_name in group_list:
            task = asyncio.ensure_future(
                api_add_user_to_group_or_raise(group_name, member_name, actor=self.user)
            )
            tasks.append(task)

        responses = asyncio.gather(*tasks, return_exceptions=True)
        data = await responses

        results = []
        for index, status in enumerate(data):
            group_name = group_list[index]

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
                    "group": group_name,
                    "member": member_name,
                }
            else:
                result = {
                    "success": False,
                    "status": "FAILED",
                    "message": str(status),
                    "group": group_name,
                    "member": member_name,
                }
            results.append(result)

        log.debug(log_data)
        self.write(json.dumps(results))
        self.set_header("Content-Type", "application/json")
        await self.finish()

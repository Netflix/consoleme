import sys
from operator import itemgetter
from urllib.parse import parse_qs, urlencode, urlparse

from consoleme.config import config
from consoleme.handlers.base import BaseHandler
from consoleme.lib.handler_utils import format_role_name
from consoleme.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()
group_mapping = get_plugin_by_name(config.get("plugins.group_mapping"))()
aws = get_plugin_by_name(config.get("plugins.aws"))()
auth = get_plugin_by_name(config.get("plugins.auth"))()


class AutoLoginHandler(BaseHandler):
    """Display AutoLoginHandler page."""

    def initialize(self):
        """Initialize the Tornado RequestHandler."""
        self.user = None
        self.eligible_roles = None
        self.eligible_accounts = None
        self.groups = None
        super(AutoLoginHandler, self).initialize()

    async def head(self):
        """Return a 200 for HEAD requests.
        This is mainly for health checks.
        """
        pass

    async def get(self, role=None):
        """Filter role / autologin endpoint
        ---
        get:
            description: Filter eligible roles by role input and render Index page with list of matching roles.
            responses:
                200:
                    description: Index page with filtered eligible user roles
        """
        if not role:
            self.write("You must pass an argument to this endpoint.")
            return

        role = role.lower()

        region = self.request.arguments.get("r", ["us-east-1"])[0]
        redirect = self.request.arguments.get("redirect", [""])[0]

        if not self.user:
            return

        selected_roles = await group_mapping.filter_eligible_roles(role, self)

        log_data = {
            "user": self.user,
            "function": "AutoLoginHandler.get",
            "selected_roles": selected_roles,
            "requested_role": role,
            "redirect": redirect,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        if not selected_roles:
            log_data["message"] = (
                "You do not have any roles matching your search criteria. "
                "Visit the Request Access tab to request access to a role."
            )
            log.error(log_data)
            # Not authorized
            stats.count(
                "AutoLoginHandler.get",
                tags={"user": self.user, "role": role, "authorized": False},
            )

            await self.render(
                "role_select.html",
                page_title="ConsoleMe - Console Access",
                user=self.user,
                eligible_roles=self.eligible_roles,
                eligible_accounts=self.eligible_accounts,
                itemgetter=itemgetter,
                recent_roles=True,
                error=log_data["message"],
                region=region,
                redirect=redirect,
                current_page="index",
                format_role_name=format_role_name,
                user_groups=self.groups,
                config=config,
            )
            return

        log_data[
            "message"
        ] = "Showing user authorized roles, or logging them in automatically if only one."
        log.debug(log_data)
        stats.count(
            "AutoLoginHandler.get",
            tags={
                "user": self.user,
                "selected_roles": selected_roles,
                "authorized": True,
            },
        )

        # User is authorized for one or more selected roles

        await self.render(
            "role_select.html",
            page_title="ConsoleMe - Console Access",
            user=self.user,
            eligible_roles=selected_roles,
            eligible_accounts={},
            itemgetter=itemgetter,
            recent_roles=False,
            error=None,
            region=region,
            redirect=redirect,
            current_page="index",
            format_role_name=format_role_name,
            user_groups=self.groups,
            config=config,
        )

    async def post(self):
        """
        Post to the autologin endpoint. This will attempt to retrieve credentials for the end-user.
        ---
        description: Retrieves credentials and redirects user to AWS console.
        responses:
            302:
                description: Redirects to AWS console
        """

        if not self.user:
            return
        arguments = {k: self.get_argument(k) for k in self.request.arguments}
        role = arguments.get("role")
        region = arguments.get("region")
        redirect = arguments.get("redirect")
        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "role": role,
            "region": region,
            "redirect": redirect,
            "ip": self.ip,
        }

        log_data["role"] = role
        if not role or role not in self.eligible_roles:
            # Not authorized
            stats.count(
                "index.post",
                tags={
                    "user": self.user,
                    "role": role,
                    "authorized": False,
                    "redirect": True if redirect else False,
                },
            )
            log_data["message"] = "Unauthorized role or invalid parameter passed."
            log.error(log_data)
            self.set_status(403)
            await self.render(
                "role_select.html",
                page_title="ConsoleMe - Console Access",
                current_page="index",
                user=self.user,
                eligible_roles=self.eligible_roles,
                eligible_accounts=self.eligible_accounts,
                itemgetter=itemgetter,
                recent_roles=True,
                error=log_data["message"],
                region=region or config.get("aws.region"),
                redirect=redirect,
                format_role_name=format_role_name,
                user_groups=self.groups,
                config=config,
            )
            return

        stats.count(
            "index.post",
            tags={
                "user": self.user,
                "role": role,
                "authorized": True,
                "redirect": True if redirect else False,
            },
        )

        log_data["message"] = "Incoming request"
        log.debug(log_data)

        # User is authorized
        try:
            # User-role logic:
            # User-role should come in as cm-[username or truncated username]_[N or NC]
            user_role = False
            account_id = None

            # User role must be defined as a user attribute
            if (
                self.user_role_name
                and "role/" in role
                and role.split("role/")[1] == self.user_role_name
            ):
                user_role = True
                account_id = role.split("arn:aws:iam::")[1].split(":role")[0]

            url = await aws.generate_url(
                self.user, role, region, user_role=user_role, account_id=account_id
            )
        except Exception as e:
            log_data["message"] = "Exception generating AWS console URL"
            log.error(log_data, exc_info=True)
            stats.count("index.post.exception")
            self.set_status(403)
            await self.render(
                "index.html",
                page_title="ConsoleMe - Console Access",
                current_page="index",
                user=self.user,
                eligible_roles=self.eligible_roles,
                eligible_accounts=self.eligible_accounts,
                itemgetter=itemgetter,
                recent_roles=True,
                error=f"Error assuming role: {str(e)}",
                region=region,
                redirect=redirect,
                format_role_name=format_role_name,
                user_groups=self.groups,
                config=config,
            )
            return
        if redirect:
            redirect = redirect.replace("|HASHSYMBOL|", "#")
            redirect = redirect.replace("|SEMICOLON|", ";")
            parsed_url = urlparse(url)
            parsed_url_query = parse_qs(parsed_url.query)
            parsed_url_query["Destination"] = redirect
            updated_query = urlencode(parsed_url_query, doseq=True)
            url = parsed_url._replace(query=updated_query).geturl()

        self.redirect(url)

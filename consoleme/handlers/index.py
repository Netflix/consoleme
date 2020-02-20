import sys
from operator import itemgetter
from urllib.parse import parse_qs, urlencode, urlparse

from consoleme.config import config
from consoleme.handlers.base import BaseHandler
from consoleme.lib.handler_utils import format_role_name
from consoleme.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()
aws = get_plugin_by_name(config.get("plugins.aws"))()
auth = get_plugin_by_name(config.get("plugins.auth"))()


class IndexApiHandler:
    async def get(self):
        # Return everything the index page needs to render
        pass


class IndexHandler(BaseHandler):
    def initialize(self) -> None:
        """Initialize the Tornado RequestHandler."""
        self.user = None
        self.eligible_roles = None
        self.eligible_accounts = None
        self.groups = None

    async def head(self):
        """Return a 200 for HEAD requests.
        This is mainly for health checks.
        """
        pass

    async def get(self) -> None:
        """
        Get the index endpoint. Presents views of valid AWS roles for the user.
        ---
        description: Get the index endpoint. Presents views of valid AWS roles for the user. The user can choose to log in to a role.
        responses:
            200:
                description: Index page with successful listing of user roles
        """

        if not self.user:
            return

        region = self.request.arguments.get("r", ["us-east-1"])[0]
        redirect = self.request.arguments.get("redirect", [""])[0]
        stats.count("index.get", tags={"user": self.user, "ip": self.ip})
        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "ip": self.ip,
        }

        log.debug(log_data)
        await self.render(
            "index.html",
            page_title="ConsoleMe - Console Access",
            current_page="index",
            user=self.user,
            eligible_roles=self.eligible_roles,
            eligible_accounts=self.eligible_accounts,
            itemgetter=itemgetter,
            recent_roles=True,
            error=None,
            region=region,
            redirect=redirect,
            format_role_name=format_role_name,
            user_groups=self.groups,
            config=config,
        )

    async def post(self):
        """
        Post to the index endpoint. This will attempt to retrieve credentials for the end-user.
        ---
        description: Retrieves credentials and redirects user to AWS console.
        responses:
            302:
                description: Redirects to AWS console
        """

        if not self.user:
            return
        arguments = {k: self.get_argument(k) for k in self.request.arguments}
        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "ip": self.ip,
        }

        role = arguments.get("role")
        region = arguments.get("region")
        redirect = arguments.get("redirect")
        log_data["role"] = role
        if not role or role not in self.eligible_roles:
            # Not authorized
            stats.count(
                "index.post",
                tags={
                    "user": self.user,
                    "role": role,
                    "authorized": False,
                    "ip": self.ip,
                },
            )
            log_data["message"] = "Unauthorized role or invalid parameter passed."
            log.error(log_data)
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
            tags={"user": self.user, "role": role, "authorized": True, "ip": self.ip},
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
            if self.user_role_name and role.split("role/")[1] == self.user_role_name:
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
            parsed_url = urlparse(url)
            parsed_url_query = parse_qs(parsed_url.query)
            parsed_url_query["Destination"] = redirect
            updated_query = urlencode(parsed_url_query, doseq=True)
            url = parsed_url._replace(query=updated_query).geturl()

        self.redirect(url)

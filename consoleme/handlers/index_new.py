from consoleme.config import config
from consoleme.handlers.base import BaseHandler
from consoleme.lib.loader import WebpackLoader
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.handler_utils import format_role_name

import json
from operator import itemgetter
from urllib.parse import parse_qs, urlencode, urlparse


log = config.get_logger()
aws = get_plugin_by_name(config.get("plugins.aws"))()
auth = get_plugin_by_name(config.get("plugins.auth"))()


# TODO, move followings to util file
async def _filter_by_extension(bundle, extension):
    """Return only files with the given extension"""
    for chunk in bundle:
        if chunk["name"].endswith(".{0}".format(extension)):
            yield chunk


async def _get_bundle(name, extension, config):
    loader = WebpackLoader(name=name, config=config)
    bundle = loader.get_bundle(name)
    if extension:
        bundle = await _filter_by_extension(bundle, extension)
    return bundle


async def get_as_tags(name="main", extension=None, config=config, attrs=""):
    """
    Get a list of formatted <script> & <link> tags for the assets in the
    named bundle.

    :param bundle_name: The name of the bundle
    :param extension: (optional) filter by extension, eg. 'js' or 'css'
    :param config: (optional) the name of the configuration
    :return: a list of formatted tags as strings
    """

    bundle = await _get_bundle(name, extension, config)
    tags = []
    for chunk in bundle:
        if chunk["name"].endswith((".js", ".js.gz")):
            tags.append(
                ('<script type="text/javascript" src="{0}" {1}></script>').format(
                    chunk["url"], attrs
                )
            )
        elif chunk["name"].endswith((".css", ".css.gz")):
            tags.append(
                ('<link type="text/css" href="{0}" rel="stylesheet" {1}/>').format(
                    chunk["url"], attrs
                )
            )
    return tags


class IndexNewHandler(BaseHandler):
    # def check_xsrf_cookie(self):
    #     # CSRF token is not needed since this is protected by raw OAuth2 tokens
    #     pass

    async def get(self) -> None:
        """
        Get the index endpoint
        ---
        description: Get the index endpoint.
        responses:
            200:
                description: Index page
        """

        await self.render(
            "index_new.html",
            page_title="ConsoleMe - Console Access",
            bundles=await get_as_tags(name="main", config=config),
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

        arguments = json.loads(self.request.body)
        role = arguments.get("role")
        region = arguments.get("region")

        user_role = False
        account_id = None

        # User role must be defined as a user attribute
        if self.user_role_name and role.split("role/")[1] == self.user_role_name:
            user_role = True
            account_id = role.split("arn:aws:iam::")[1].split(":role")[0]

        url = await aws.generate_url(
            self.user, role, region, user_role=user_role, account_id=account_id
        )

        self.write({
            "redirect": url
        })
        return

        # if not role or role not in self.eligible_roles:
        #     # Not authorized
        #     self.set_status(403)
        #     await self.render(
        #         "index.html",
        #         page_title="ConsoleMe - Console Access",
        #         current_page="index",
        #         user=self.user,
        #         eligible_roles=self.eligible_roles,
        #         eligible_accounts=self.eligible_accounts,
        #         itemgetter=itemgetter,
        #         recent_roles=True,
        #         error=log_data["message"],
        #         region=region or config.get("aws.region"),
        #         redirect=redirect,
        #         format_role_name=format_role_name,
        #         user_groups=self.groups,
        #         config=config,
        #     )
        #     return

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


class SelectRolesHandler(BaseHandler):
    def initialize(self):
        self.user: str = None
        self.eligible_roles: list = []

    async def get(self):
        self.set_header("Content-Type", "application/json")
        payload = {
            "eligible_roles": self.eligible_roles,
            "_xsrf": self.xsrf_token.decode("utf-8")
        }
        self.write(json.dumps(payload))
        await self.finish()

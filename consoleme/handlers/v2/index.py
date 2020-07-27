import re
from operator import itemgetter

import ujson as json

from consoleme.config import config
from consoleme.handlers.base import BaseHandler
from consoleme.lib.handler_utils import format_role_name
from consoleme.lib.loader import WebpackLoader
from consoleme.lib.plugins import get_plugin_by_name

log = config.get_logger()
aws = get_plugin_by_name(config.get("plugins.aws"))()
auth = get_plugin_by_name(config.get("plugins.auth"))()
stats = get_plugin_by_name(config.get("plugins.metrics"))()

ARN_REGEX = (
    r"^arn:aws:iam::(\d{12}):role\/(.+)"
)  # TODO: This should be in config or use policy universe/policy sentry


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


class LandingTableConfigHandler(BaseHandler):
    async def get(self):
        """
        /landing_table_config
        ---
        get:
            description: Retrieve Landing Table Configuration
            responses:
                200:
                    description: Returns Landing Table Configuration
        """
        default_configuration = {
            "expandableRows": False,
            "tableName": "Select a Role to Login AWS Console",
            "tableDescription": "Followings are the accounts you are eligible to sign-in with permission associated the role you are given.",
            "dataEndpoint": "/landing",
            "sortable": False,
            "totalRows": 1000,
            "rowsPerPage": 50,
            "serverSideFiltering": False,
            "columns": [
                {"placeholder": "Account Name", "key": "account_name", "type": "input"},
                {"placeholder": "Account ID", "key": "account_id", "type": "input"},
                {"placeholder": "Role Name", "key": "role_name", "type": "input"},
                # TODO: Support getting CLI Credentials via web interface
                # {
                #     "placeholder": "CLI",
                #     "key": "credential",
                #     "type": "icon",
                #     "icon": "key",
                # },
                {
                    "placeholder": "Console",
                    "key": "redirect",
                    "type": "icon",
                    "icon": "sign-in",
                    "onClick": {"action": "redirect"},
                },
            ],
        }

        table_configuration = config.get(
            "LandingTableConfigHandler.configuration", default_configuration
        )

        self.write(table_configuration)


class IndexHandler(BaseHandler):
    async def get(self) -> None:
        """
        Get the index endpoint
        ---
        description: Get the index endpoint.
        responses:
            200:
                description: Index page
        """

        region = self.request.arguments.get("r", ["us-east-1"])[0]
        redirect = self.request.arguments.get("redirect", [""])[0]

        await self.render(
            "landing.html",
            page_title="ConsoleMe - Console Access",
            # bundles=await get_as_tags(name="main", config=config),
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
        Post to the index endpoint. This will attempt to retrieve roles and its credentials.
        ---
        description: Retrieves roles and its credentials for AWS console access.
        responses:
            200:
                description: Redirects to AWS console
        """

        roles = []
        for arn in self.eligible_roles:
            match = re.match(ARN_REGEX, arn)
            account_id = match.group(1)
            role_name = match.group(2).split("/")[-1]
            account_name = self.eligible_accounts.get(account_id, "")
            roles.append(
                {
                    "arn": arn,
                    "account_name": account_name,
                    "account_id": account_id,
                    "role_name": f"[{role_name}](/policies/edit/{arn.split(':')[4]}/iamrole/{arn.split('/')[-1]})",
                    "credential": "",
                    "redirect": f"/role/{arn}",
                }
            )

        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(roles, escape_forward_slashes=False))
        await self.finish()

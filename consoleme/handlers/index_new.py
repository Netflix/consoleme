from consoleme.config import config
from consoleme.handlers.base import BaseHandler
from consoleme.lib.loader import WebpackLoader

import json

log = config.get_logger()

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


class SelectRolesHandler(BaseHandler):
    def initialize(self):
        self.user: str = None
        self.eligible_roles: list = []

    async def get(self):
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(self.eligible_roles))
        await self.finish()

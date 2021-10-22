"""Entrypoint for ConsoleMe. To run service, set CONFIG_LOCATION environmental variable and run
python -m consoleme.__main__"""

import asyncio
import logging
import os

import tornado.autoreload
import tornado.httpserver
import tornado.ioloop
import uvloop
from tornado.platform.asyncio import AsyncIOMainLoop

from consoleme.config import config
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.routes import make_app

logging.basicConfig(level=logging.DEBUG, format=config.get("logging.format"))
logging.getLogger("urllib3.connectionpool").setLevel(logging.CRITICAL)
stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
log = config.get_logger()


def main():
    if config.get("sso.create_mock_jwk"):
        app = make_app(jwt_validator=lambda x: {})
    else:
        app = make_app()
    return app


if config.get("tornado.uvloop", True):
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
AsyncIOMainLoop().install()
app = main()


def init():
    port = config.get("tornado.port")
    stats.count("start")

    server = tornado.httpserver.HTTPServer(app)

    if port:
        server.bind(port, address=config.get("tornado.address"))

    server.start()  # forks one process per cpu

    if config.get("tornado.debug", False):
        for directory, _, files in os.walk("consoleme/templates"):
            [
                tornado.autoreload.watch(directory + "/" + f)
                for f in files
                if not f.startswith(".")
            ]
    log.debug({"message": "Server started"})
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    init()

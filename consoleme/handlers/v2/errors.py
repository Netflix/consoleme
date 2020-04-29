import ujson as json
from typing import Dict
from typing import Optional

from tornado.web import RequestHandler

from consoleme.config import config
from consoleme.handlers.base import BaseJSONHandler
from consoleme.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("plugins.metrics"))()

log = config.get_logger()


class ErrorHandler(BaseJSONHandler):
    def __init__(self, status, *args, **kwargs):
        self.status = status
        super().__init__(jwt_validator=lambda x: {}, *args, **kwargs)

    async def get(self):
        self.write_error(self.status)

    async def head(self):
        self.write_error(self.status)

    async def put(self):
        self.write_error(self.status)

    async def patch(self):
        self.write_error(self.status)

    async def post(self):
        self.write_error(self.status)

    async def delete(self):
        self.write_error(self.status)


class NotFoundHandler(ErrorHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(404, *args, **kwargs)

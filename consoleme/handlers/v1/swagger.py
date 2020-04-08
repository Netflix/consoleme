import tornado.web

from consoleme.config import config


class SwaggerHandler(tornado.web.RequestHandler):
    """Tornado request handler for serving Swagger"""

    async def get(self):
        await self.render("swagger.html")


class SwaggerJsonGenerator(tornado.web.RequestHandler):
    """Tornado request handler for serving Swagger file"""

    async def get(self):
        self.write(config.api_spec)

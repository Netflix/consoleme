from consoleme.handlers.base import BaseHandler


class AuthHandler(BaseHandler):
    async def prepare(self):
        try:
            if self.request.method.lower() in ["options", "post"]:
                return
            await super(AuthHandler, self).prepare()
        except:
            # NoUserException
            raise

    async def get(self):
        self.write("")

    async def post(self):
        self.write("")

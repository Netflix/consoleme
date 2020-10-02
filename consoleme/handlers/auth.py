import time

from consoleme.handlers.base import BaseHandler


class AuthHandler(BaseHandler):
    async def prepare(self):
        try:
            if self.request.method.lower() in ["options", "post"]:
                return
            await super(AuthHandler, self).prepare()
        except:  # noqa
            # NoUserException
            raise

    async def get(self):
        self.write(
            {
                "authCookieExpiration": self.auth_cookie_expiration,
                "currentServerTime": int(time.time()),
            }
        )

    async def post(self):
        self.write(
            {
                "authCookieExpiration": self.auth_cookie_expiration,
                "currentServerTime": int(time.time()),
            }
        )

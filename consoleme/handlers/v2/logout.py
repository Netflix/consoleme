import sys

from consoleme.config import config
from consoleme.handlers.base import BaseHandler
from consoleme.lib.web import handle_generic_error_response
from consoleme.models import WebResponse

log = config.get_logger()


class LogOutHandler(BaseHandler):
    async def get(self):
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Attempting to log out user",
            "user-agent": self.request.headers.get("User-Agent"),
            "ip": self.ip,
        }
        if not config.get("auth.set_auth_cookie"):
            await handle_generic_error_response(
                self,
                "Unable to log out",
                [
                    (
                        "Configuration value `auth.set_auth_cookie` is not enabled. "
                        "ConsoleMe isn't able to delete an auth cookie if setting auth "
                        "cookies is not enabled."
                    )
                ],
                400,
                "logout_failure",
                log_data,
            )
            return
        cookie_name: str = config.get("auth_cookie_name", "consoleme_auth")
        if not cookie_name:
            await handle_generic_error_response(
                self,
                "Unable to log out",
                [
                    (
                        "Configuration value `auth_cookie_name` is not set. "
                        "ConsoleMe isn't able to delete an auth cookie if the auth cookie name "
                        "is not known."
                    )
                ],
                400,
                "logout_failure",
                log_data,
            )
            return
        self.clear_cookie(cookie_name)

        extra_auth_cookies: list = config.get("auth.extra_auth_cookies", [])
        for cookie in extra_auth_cookies:
            self.clear_cookie(cookie)

        redirect_url: str = config.get("auth.logout_redirect_url", "/")
        res = WebResponse(
            status="redirect",
            redirect_url=redirect_url,
            status_code=200,
            reason="logout_redirect",
            message="User has successfully logged out. Redirecting to landing page",
        )
        log.debug({**log_data, "message": "Successfully logged out user."})
        self.write(res.json())

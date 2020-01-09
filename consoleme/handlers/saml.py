from asgiref.sync import sync_to_async
from onelogin.saml2.utils import OneLogin_Saml2_Utils

from consoleme.config import config
from consoleme.handlers.base import BaseHandler
from consoleme.lib.crypto import Crypto
from consoleme.lib.jwt import generate_jwt_token
from consoleme.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()
crypto = Crypto()
auth = get_plugin_by_name(config.get("plugins.auth"))()


class SamlHandler(BaseHandler):
    async def post(self, endpoint):
        req = await self.prepare_tornado_request_for_saml()
        auth = await self.init_saml_auth(req)

        if "sso" in endpoint:
            return self.redirect(auth.login())
        elif "acs" in endpoint:
            auth.process_response()
            errors = auth.get_errors()
            not_auth_warn = not await sync_to_async(auth.is_authenticated)()
            if not_auth_warn:
                self.write("User is not authenticated")
                await self.finish()
                return
            if len(errors) == 0:
                saml_attributes = await sync_to_async(auth.get_attributes)()
                email = saml_attributes[
                    config.get("get_user_by_saml_settings.attributes.email")
                ]
                if isinstance(email, list) and len(email) > 0:
                    email = email[0]
                groups = saml_attributes[
                    config.get("get_user_by_saml_settings.attributes.groups")
                ]

                self_url = await sync_to_async(OneLogin_Saml2_Utils.get_self_url)(req)

                encoded_cookie = await generate_jwt_token(email, groups)
                self.set_cookie(config.get("auth_cookie_name"), encoded_cookie)
                if "RelayState" in self.request.arguments and self_url != self.request.arguments[
                    "RelayState"
                ][
                    0
                ].decode(
                    "utf-8"
                ):
                    return self.redirect(
                        auth.redirect_to(
                            self.request.arguments["RelayState"][0].decode("utf-8")
                        )
                    )

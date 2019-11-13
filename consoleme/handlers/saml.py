from datetime import datetime, timedelta

from consoleme.config import config
from consoleme.handlers.base import BaseHandler
from consoleme.lib.crypto import Crypto
from consoleme.lib.plugins import get_plugin_by_name

import jwt
from asgiref.sync import sync_to_async
from onelogin.saml2.utils import OneLogin_Saml2_Utils

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()
crypto = Crypto()
auth = get_plugin_by_name(config.get("plugins.auth"))()


class SamlHandler(BaseHandler):
    async def post(self, endpoint):
        req = await self.prepare_tornado_request_for_saml()
        auth = await self.init_saml_auth(req)
        session = {}

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
                session["samlUserdata"] = await sync_to_async(auth.get_attributes)()
                session["samlNameId"] = await sync_to_async(auth.get_nameid)()
                # Set an issued-at time
                session["iat"] = datetime.utcnow()
                # Set an expiration time
                session["exp"] = datetime.utcnow() + timedelta(
                    hours=config.get(
                        "get_user_by_saml_settings.jwt.expiration_hours", 1
                    )
                )
                # Set a not-before-time
                session["nbf"] = datetime.utcnow() - timedelta(seconds=5)
                session["samlSessionIndex"] = await sync_to_async(
                    auth.get_session_index
                )()
                self_url = await sync_to_async(OneLogin_Saml2_Utils.get_self_url)(req)
                saml_jwt_secret = config.get("saml_jwt_secret")
                if not saml_jwt_secret:
                    raise Exception("'saml_jwt_secret' configuration value is not set.")
                # Set secure cookie here
                encoded_cookie = await sync_to_async(jwt.encode)(
                    session, saml_jwt_secret, algorithm="HS256"
                )
                self.set_cookie("consoleme_auth", encoded_cookie)
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

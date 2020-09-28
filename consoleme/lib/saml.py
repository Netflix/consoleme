import sys

from asgiref.sync import sync_to_async
from onelogin.saml2.errors import OneLogin_Saml2_Error

from consoleme.config import config
from consoleme.exceptions.exceptions import WebAuthNError

log = config.get_logger()


async def authenticate_user_by_saml(request):
    log_data = {"function": f"{__name__}.{sys._getframe().f_code.co_name}"}
    saml_req = await request.prepare_tornado_request_for_saml()
    saml_auth = await request.init_saml_auth(saml_req)
    force_redirect = request.request.arguments.get("force_redirect", [True])[0]
    if force_redirect and isinstance(force_redirect, bytes):
        force_redirect = force_redirect.decode("utf-8")
    if force_redirect in ["false", "False"]:
        force_redirect = False
    try:
        await sync_to_async(saml_auth.process_response)()
    except OneLogin_Saml2_Error as e:
        log_data["error"] = e
        log.error(log_data)
        if force_redirect:
            saml_auth.login(),
        else:
            request.write(
                {
                    "type": "redirect",
                    "redirect_url": saml_auth.login(),
                }
            )
            return

    saml_errors = await sync_to_async(saml_auth.get_errors)()
    if saml_errors:
        log_data["error"] = saml_errors
        log.error(log_data)
        raise WebAuthNError(reason=saml_errors)
    not_auth_warn = not await sync_to_async(saml_auth.is_authenticated)()
    if not_auth_warn:
        if force_redirect:
            saml_auth.login(),
        else:
            request.write(
                {
                    "type": "redirect",
                    "redirect_url": saml_auth.login(),
                }
            )

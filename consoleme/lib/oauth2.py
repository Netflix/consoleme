import base64
import sys
from urllib.parse import urlencode, urlparse, parse_qs

import jwt
import tornado.httpclient
import ujson as json
from tornado import httputil

from consoleme.config import config
from consoleme.lib.jwt import generate_jwt_token

log = config.get_logger()


async def authenticate_user_by_oauth2(request):
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {"function": function}
    code = request.get_argument("code", None)
    client_id = config.get("oidc_secrets.client_id")
    client_secret = config.get("oidc_secrets.secret")
    redirect_uri = (
        f"{request.request.protocol}://{request.request.host}{request.request.uri}"
    )
    if code is None:
        args = {"response_type": "code"}
        client_scope = config.get("oidc_secrets.client_scope")
        if request.request.uri is not None:
            args["redirect_uri"] = redirect_uri
        if client_id is not None:
            args["client_id"] = client_id
        if client_scope:
            args["scope"] = " ".join(client_scope)
        request.redirect(
            httputil.url_concat(
                config.get("get_user_by_oidc_settings.authorize_url"), args
            )
        )
        return
    try:
        # exchange the authorization code with the access token
        http_client = tornado.httpclient.AsyncHTTPClient()
        grant_type = "authorization_code"
        authorization_header = f"{client_id}:{client_secret}"
        authorization_header_encoded = base64.b64encode(
            authorization_header.encode("UTF-8")
        ).decode("UTF-8")
        url = f'{config.get("get_user_by_oidc_settings.token_endpoint")}'

        token_exchange_response = await http_client.fetch(
            url,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": "Basic %s" % authorization_header_encoded,
                "Accept": "application/json",
            },
            body=f"grant_type={grant_type}&code={code}&redirect_uri={redirect_uri}",
        )

        token_exchange_response_body_dict = json.loads(token_exchange_response.body)

        access_token = token_exchange_response_body_dict.get("access_token")
        jwt_verify = config.get("get_user_by_oidc_settings.jwt_verify")
        if jwt_verify:
            raise NotImplementedError("JWT verification not implemented yet.")
        decoded_token = jwt.decode(access_token, verify=jwt_verify)
        email = decoded_token[config.get("get_user_by_oidc_settings.jwt_email_key")]
        groups = decoded_token[config.get("get_user_by_oidc_settings.jwt_groups_key")]

        if config.get("auth.set_auth_cookie"):
            encoded_cookie = await generate_jwt_token(email, groups)
            request.set_cookie(config.get("auth_cookie_name"), encoded_cookie)
        redirect_uri = urlparse(redirect_uri)
        query = parse_qs(redirect_uri.query, keep_blank_values=True)
        query.pop("session_state", None)
        query.pop("code", None)
        redirect_uri = redirect_uri._replace(query=urlencode(query, True))
        request.redirect(redirect_uri.geturl())
        return
    except Exception as e:
        log_data["error"] = e
        log.error(log_data)
        return

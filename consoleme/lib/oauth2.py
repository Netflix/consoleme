import base64
import sys
from urllib.parse import parse_qs, urlencode, urlparse

import jwt
import tornado.httpclient
import ujson as json
from jwt.algorithms import RSAAlgorithm
from tornado import httputil

from consoleme.config import config
from consoleme.exceptions.exceptions import MissingConfigurationValue
from consoleme.lib.jwt import generate_jwt_token

log = config.get_logger()


async def populate_oidc_config():
    http_client = tornado.httpclient.AsyncHTTPClient()
    metadata_url = config.get("get_user_by_oidc_settings.metadata_url")
    oidc_config = {}
    if metadata_url:
        res = await http_client.fetch(
            metadata_url,
            method="GET",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        oidc_config = json.loads(res.body)
    else:
        authorization_endpoint = config.get(
            "get_user_by_oidc_settings.authorization_endpoint"
        )
        token_endpoint = config.get("get_user_by_oidc_settings.token_endpoint")
        jwks_uri = config.get("get_user_by_oidc_settings.jwks_uri")
        if not (authorization_endpoint or token_endpoint or jwks_uri):
            raise MissingConfigurationValue("Missing OAuth2 Configuration.")
        oidc_config = {
            "authorization_endpoint": authorization_endpoint,
            "token_endpoint": token_endpoint,
            "jwks_uri": jwks_uri,
        }
    client_id = config.get("oidc_secrets.client_id")
    client_secret = config.get("oidc_secrets.secret")
    if not (client_id or client_secret):
        raise MissingConfigurationValue("Missing OAuth2 Secrets")
    oidc_config["client_id"] = client_id
    oidc_config["client_secret"] = client_secret
    # Fetch jwks_uri for jwt validation
    res = await http_client.fetch(
        oidc_config["jwks_uri"],
        method="GET",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    oidc_config["jwks_data"] = json.loads(res.body)
    oidc_config["jwt_keys"] = {
        k["kid"]: RSAAlgorithm.from_jwk(json.dumps(k))
        for k in oidc_config["jwks_data"]["keys"]
    }

    return oidc_config


async def authenticate_user_by_oauth2(request):
    oidc_config = await populate_oidc_config()

    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {"function": function}
    code = request.get_argument("code", None)
    redirect_uri = f"{request.request.protocol}://{request.request.host}/"
    if code is None:
        args = {"response_type": "code"}
        client_scope = config.get("oidc_secrets.client_scope")
        if request.request.uri is not None:
            args["redirect_uri"] = redirect_uri
        args["client_id"] = oidc_config["client_id"]
        if client_scope:
            args["scope"] = " ".join(client_scope)
        args["state"] = request.ip
        request.redirect(
            httputil.url_concat(oidc_config["authorization_endpoint"], args)
        )
        return
    try:
        # exchange the authorization code with the access token
        http_client = tornado.httpclient.AsyncHTTPClient()
        grant_type = config.get(
            "get_user_by_oidc_settings.grant_type", "authorization_code"
        )
        authorization_header = (
            f"{oidc_config['client_id']}:{oidc_config['client_secret']}"
        )
        authorization_header_encoded = base64.b64encode(
            authorization_header.encode("UTF-8")
        ).decode("UTF-8")
        url = f"{oidc_config['token_endpoint']}"
        client_scope = config.get("oidc_secrets.client_scope")
        if client_scope:
            client_scope = " ".join(client_scope)
        token_exchange_response = await http_client.fetch(
            url,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": "Basic %s" % authorization_header_encoded,
                "Accept": "application/json",
            },
            body=f"grant_type={grant_type}&code={code}&redirect_uri={redirect_uri}&scope={client_scope}",
        )

        token_exchange_response_body_dict = json.loads(token_exchange_response.body)

        id_token = token_exchange_response_body_dict.get(
            config.get("get_user_by_oidc_settings.id_token_response_key", "id_token")
        )
        access_token = token_exchange_response_body_dict.get(
            config.get(
                "get_user_by_oidc_settings.access_token_response_key", "access_token"
            )
        )
        jwt_verify = config.get("get_user_by_oidc_settings.jwt_verify")
        if jwt_verify:
            header = jwt.get_unverified_header(id_token)
            key_id = header["kid"]
            algorithm = header["alg"]
            pub_key = oidc_config["jwt_keys"][key_id]
            # This will raises errors if the audience isn't right or if the token is expired or has other errors.
            decoded_id_token = jwt.decode(
                id_token,
                pub_key,
                audience=oidc_config["client_id"],
                algorithm=algorithm,
            )

            header = jwt.get_unverified_header(access_token)
            key_id = header["kid"]
            algorithm = header["alg"]
            pub_key = oidc_config["jwt_keys"][key_id]
            # This will raises errors if the audience isn't right or if the token is expired or has other errors.
            decoded_access_token = jwt.decode(
                access_token,
                pub_key,
                audience=config.get("get_user_by_oidc_settings.access_token_audience"),
                algorithm=algorithm,
            )
        else:
            decoded_id_token = jwt.decode(id_token, verify=jwt_verify)
            decoded_access_token = jwt.decode(access_token, verify=jwt_verify)
        email = decoded_id_token.get(
            config.get("get_user_by_oidc_settings.jwt_email_key", "email")
        )
        groups = decoded_access_token.get(
            config.get("get_user_by_oidc_settings.jwt_groups_key", "groups")
        )

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

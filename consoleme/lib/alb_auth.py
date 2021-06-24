import base64
import json
import sys

import jwt
import requests
import tornado.httpclient
from jwt.algorithms import ECAlgorithm, RSAAlgorithm
from jwt.exceptions import (
    ExpiredSignatureError,
    ImmatureSignatureError,
    InvalidAudienceError,
    InvalidIssuedAtError,
    InvalidIssuerError,
)
from okta_jwt.utils import verify_exp, verify_iat

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    MissingConfigurationValue,
    UnableToAuthenticate,
)

log = config.get_logger()


async def populate_oidc_config():
    http_client = tornado.httpclient.AsyncHTTPClient()
    metadata_url = config.get(
        "get_user_by_aws_alb_auth_settings.access_token_validation.metadata_url"
    )

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
        jwks_uri = config.get(
            "get_user_by_aws_alb_auth_settings.access_token_validation.jwks_uri"
        )
        if not jwks_uri:
            raise MissingConfigurationValue("Missing OIDC Configuration.")
        oidc_config = {
            "jwks_uri": jwks_uri,
        }

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
    oidc_config["jwt_keys"] = {}
    for k in oidc_config["jwks_data"]["keys"]:
        key_type = k["kty"]
        key_id = k["kid"]
        if key_type == "RSA":
            oidc_config["jwt_keys"][key_id] = RSAAlgorithm.from_jwk(json.dumps(k))
        elif key_type == "EC":
            oidc_config["jwt_keys"][key_id] = ECAlgorithm.from_jwk(json.dumps(k))
    oidc_config["aud"] = config.get(
        "get_user_by_aws_alb_auth_settings.access_token_validation.client_id"
    )
    return oidc_config


async def authenticate_user_by_alb_auth(request):
    aws_alb_auth_header_name = config.get(
        "get_user_by_aws_alb_auth_settings.aws_alb_auth_header_name", "X-Amzn-Oidc-Data"
    )
    aws_alb_claims_header_name = config.get(
        "get_user_by_aws_alb_auth_settings.aws_alb_claims_header_name",
        "X-Amzn-Oidc-Accesstoken",
    )
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {"function": function}
    encoded_auth_jwt = request.request.headers.get(aws_alb_auth_header_name)
    access_token = request.request.headers.get(aws_alb_claims_header_name)
    if not encoded_auth_jwt:
        raise Exception(f"Missing header: {aws_alb_auth_header_name}")
    if not access_token:
        raise Exception(f"Missing header: {aws_alb_claims_header_name}")

    jwt_headers = encoded_auth_jwt.split(".")[0]
    decoded_jwt_headers = base64.b64decode(jwt_headers)
    decoded_jwt_headers = decoded_jwt_headers.decode("utf-8")
    decoded_json = json.loads(decoded_jwt_headers)
    kid = decoded_json["kid"]
    # Step 2: Get the public key from regional endpoint
    url = "https://public-keys.auth.elb." + config.region + ".amazonaws.com/" + kid
    req = requests.get(url)
    pub_key = req.text
    # Step 3: Get the payload
    payload = jwt.decode(encoded_auth_jwt, pub_key, algorithms=["ES256"])
    email = payload.get(
        config.get("get_user_by_aws_alb_auth_settings.jwt_email_key", "email")
    )

    if not email:
        raise UnableToAuthenticate("Unable to determine user from ID Token")

    # Step 4: Parse the Access Token
    # User has already passed ALB auth and successfully authenticated
    access_token_pub_key = None
    jwt_verify = config.get("get_user_by_aws_alb_auth_settings.jwt_verify", True)
    access_token_verify_options = {"verify_signature": jwt_verify}
    oidc_config = {}
    algorithm = None
    try:
        if jwt_verify:
            oidc_config = await populate_oidc_config()
            header = jwt.get_unverified_header(access_token)
            key_id = header["kid"]
            algorithm = header["alg"]
            if algorithm == "none" or not algorithm:
                raise UnableToAuthenticate(
                    "Access Token header does not specify a signing algorithm."
                )
            access_token_pub_key = oidc_config["jwt_keys"][key_id]

        decoded_access_token = jwt.decode(
            access_token,
            access_token_pub_key,
            algorithms=[algorithm],
            options=access_token_verify_options,
            audience=oidc_config.get("aud"),
            issuer=oidc_config.get("issuer"),
        )
        # Step 5: Verify the access token.
        if not jwt_verify:
            verify_exp(access_token)
            verify_iat(access_token)

        # Extract groups from tokens, checking both because IdPs aren't consistent here
        for token in [decoded_access_token, payload]:
            groups = token.get(
                config.get("get_user_by_aws_alb_auth_settings.jwt_groups_key", "groups")
            )
            if groups:
                break

    except jwt.exceptions.DecodeError as e:
        # This exception occurs when the access token is not JWT-parsable. It is expected with some IdPs.
        log.debug(
            {
                **log_data,
                "message": (
                    "Unable to decode claims token. This is expected for some Identity Providers."
                ),
                "error": e,
                "user": email,
            }
        )
        log.debug(log_data, exc_info=True)
        groups = []
    except (
        ExpiredSignatureError,
        ImmatureSignatureError,
        InvalidAudienceError,
        InvalidIssuedAtError,
        InvalidIssuerError,
    ) as e:
        # JWT Validation failed, log an error and revoke the ALB auth cookie
        log.debug(
            {
                **log_data,
                "message": (str(e)),
                "error": e,
                "user": email,
            }
        )
        log.debug(log_data, exc_info=True)
        request.clear_cookie("AWSELBAuthSessionCookie-0")
        request.redirect(request.request.uri)

        groups = []

    return {"user": email, "groups": groups}

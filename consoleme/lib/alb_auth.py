import base64
import json

import jwt
import requests
from okta_jwt.jwt import validate_token

from consoleme.config import config
from consoleme.exceptions.exceptions import UnableToAuthenticate


async def authenticate_user_by_alb_auth(request):
    aws_alb_auth_header_name = config.get(
        "get_user_by_aws_alb_auth_settings.aws_alb_auth_header_name", "X-Amzn-Oidc-Data"
    )
    aws_alb_claims_header_name = config.get(
        "get_user_by_aws_alb_auth_settings.aws_alb_claims_header_name",
        "X-Amzn-Oidc-Accesstoken",
    )
    encoded_auth_jwt = request.request.headers.get(aws_alb_auth_header_name)
    encoded_claims_jwt = request.request.headers.get(aws_alb_claims_header_name)
    if not encoded_auth_jwt:
        raise Exception(f"Missing header: {aws_alb_auth_header_name}")
    if not encoded_claims_jwt:
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
    try:
        access_token_jwt = jwt.decode(encoded_claims_jwt, pub_key, verify=False)
        groups = access_token_jwt.get(
            config.get("get_user_by_aws_alb_auth_settings.jwt_groups_key", "groups")
        )
        # Step 5: Verify the access token.
        validate_token(
            encoded_claims_jwt,
            access_token_jwt["iss"],
            access_token_jwt["aud"],
            access_token_jwt["cid"],
        )
    except jwt.exceptions.DecodeError:
        # Silently skip. This is usually due to a JWT that doesn't have JWT-parsable claims.
        groups = []

    return {"user": email, "groups": groups}

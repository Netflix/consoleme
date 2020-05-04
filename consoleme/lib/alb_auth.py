import base64
import json

import jwt
import requests

from consoleme.config import config


async def authenticate_user_by_alb_auth(request):
    aws_alb_auth_header_name = config.get(
        "get_user_by_aws_alb_auth_settings.aws_alb_auth_header_name", "X-Amzn-Oidc-Data"
    )
    encoded_jwt = request.request.headers.get(aws_alb_auth_header_name)
    if not encoded_jwt:
        raise Exception(f"Missing header: {aws_alb_auth_header_name}")

    jwt_headers = encoded_jwt.split(".")[0]
    decoded_jwt_headers = base64.b64decode(jwt_headers)
    decoded_jwt_headers = decoded_jwt_headers.decode("utf-8")
    decoded_json = json.loads(decoded_jwt_headers)
    kid = decoded_json["kid"]
    # Step 2: Get the public key from regional endpoint
    url = "https://public-keys.auth.elb." + config.region + ".amazonaws.com/" + kid
    req = requests.get(url)
    pub_key = req.text
    # Step 3: Get the payload
    payload = jwt.decode(encoded_jwt, pub_key, algorithms=["ES256"])
    email = payload.get(config.get("get_user_by_aws_alb_auth_settings.jwt_email_key"))
    groups = payload.get(config.get("get_user_by_aws_alb_auth_settings.jwt_groups_key"))
    return {"user": email, "groups": groups}

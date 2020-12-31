from datetime import datetime, timedelta

import jwt
from asgiref.sync import sync_to_async

from consoleme.config import config


async def generate_jwt_token(
    email,
    groups,
    nbf=datetime.utcnow() - timedelta(seconds=5),
    iat=datetime.utcnow(),
    exp=datetime.utcnow() + timedelta(hours=config.get("jwt.expiration_hours", 1)),
):
    jwt_secret = config.get("jwt_secret")
    if not jwt_secret:
        raise Exception("'jwt_secret' configuration value is not set.")
    session = {
        "nbf": nbf,
        "iat": iat,
        "exp": exp,
        config.get("jwt.attributes.email", "email"): email,
        config.get("jwt.attributes.groups", "groups"): groups,
    }

    encoded_cookie = await sync_to_async(jwt.encode)(
        session, jwt_secret, algorithm="HS256"
    )

    return encoded_cookie


async def validate_and_return_jwt_token(auth_cookie):
    jwt_secret = config.get("jwt_secret")

    if not jwt_secret:
        raise Exception(f"{config.get('jwt_secret')} configuration value is not set.")
    try:
        decoded_jwt = jwt.decode(auth_cookie, jwt_secret, algorithm="HS256")
        email = decoded_jwt.get(config.get("jwt.attributes.email", "email"))
        groups = decoded_jwt.get(config.get("jwt.attributes.groups", "groups"), [])
        exp = decoded_jwt.get("exp")

        return {
            "user": email,
            "groups": groups,
            "iat": decoded_jwt.get("iat"),
            "exp": exp,
        }
    except (jwt.ExpiredSignatureError, jwt.InvalidSignatureError, jwt.DecodeError):
        # Force user to reauth.
        return False

import sys
import uuid
from datetime import datetime, timedelta

import pytz
import tornado.web
import ujson as json
from asgiref.sync import async_to_sync

from consoleme.config import config
from consoleme.exceptions.exceptions import MissingConfigurationValue
from consoleme.handlers.base import BaseHandler
from consoleme.lib.jwt import generate_jwt_token
from consoleme.lib.redis import RedisHandler

log = config.get_logger()
red = async_to_sync(RedisHandler().redis)()


class ChallengeGeneratorHandler(tornado.web.RequestHandler):
    """
    Challenge URLs are an alternative to mutual TLS for authenticating CLI clients of ConsoleMe.

    If Challenge Token auth is enabled, this will generate time-sensitive challenge token urls that end-users
    will be required to authenticate to. One authentication is verified, clients will be able to retrieve a
    signed jwt that clients will be able to pass to ConsoleMe for authn/authz.

    The ChallengeUrlGenerator endpoint must be unauthenticated because the CLI client will be requesting URLs
    """

    async def get(self, user):
        if not config.get("challenge_url.enabled", False):
            raise MissingConfigurationValue(
                "Challenge URL Authentication is not enabled in ConsoleMe's configuration"
            )
        ip = self.request.headers.get("X-Forwarded-For", self.request.remote_ip).split(
            ","
        )
        if isinstance(ip, list):
            ip = ip[0]

        token = str(uuid.uuid4())
        entry = {
            "ttl": int(
                (
                    datetime.utcnow().replace(tzinfo=pytz.UTC) + timedelta(minutes=2)
                ).timestamp()
            ),
            "ip": ip,
            "status": "pending",
            "user": user,
        }
        red.hset(
            config.get("challenge_url.redis_key", "TOKEN_CHALLENGES_TEMP"),
            token,
            json.dumps(entry),
        )

        challenge_url = "{url}/challenge_validator/{token}".format(
            url=config.get("url"), token=token
        )
        polling_url = "{url}/noauth/v1/challenge_poller/{token}".format(
            url=config.get("url"), token=token
        )
        self.write({"challenge_url": challenge_url, "polling_url": polling_url})

        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "challenge_url": challenge_url,
            "polling_url": polling_url,
            "message": "Incoming request",
            "ip": ip,
            "user": user,
        }
        log.debug(log_data)


class ChallengeValidatorHandler(BaseHandler):
    """

    This is the challenge authentication endpoint.
    Once the user has authenticated successfully, we validate their information and mark the challenge as successful.

    """

    async def get(self, requested_challenge_token):
        if not config.get("challenge_url.enabled", False):
            raise MissingConfigurationValue(
                "Challenge URL Authentication is not enabled in ConsoleMe's configuration"
            )
        endpoint = self.kwargs.get("type")
        ip = self.request.headers.get("X-Forwarded-For", self.request.remote_ip).split(
            ","
        )
        if isinstance(ip, list):
            ip = ip[0]
        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "requested_challenge_token": requested_challenge_token,
            "message": "Incoming request",
            "ip": ip,
        }
        log.debug(log_data)

        all_challenges = red.hgetall(
            config.get("challenge_url.redis_key", "TOKEN_CHALLENGES_TEMP")
        )
        current_time = int(datetime.utcnow().replace(tzinfo=pytz.UTC).timestamp())
        expired_challenge_tokens = []
        # Delete expired tokens
        if all_challenges:
            for token, challenge_j in all_challenges.items():
                challenge = json.loads(challenge_j)
                if challenge.get("ttl", 0) < current_time:
                    expired_challenge_tokens.append(token)
            if expired_challenge_tokens:
                red.hdel(
                    config.get("challenge_url.redis_key", "TOKEN_CHALLENGES_TEMP"),
                    *expired_challenge_tokens,
                )
        else:
            message = (
                "Unable to find a matching challenge URL. This usually means that it has expired. "
                "Please try requesting a new challenge URL."
            )
            if endpoint == "web":
                self.write(message)
            elif endpoint == "api":
                self.write({"message": message})
            return
        # Get fresh challenge for user's request
        user_challenge_j = red.hget(
            config.get("challenge_url.redis_key", "TOKEN_CHALLENGES_TEMP"),
            requested_challenge_token,
        )
        if user_challenge_j:
            # Do a double-take check on the ttl
            # Delete the token
            user_challenge = json.loads(user_challenge_j)
            if user_challenge.get("ttl", 0) < current_time:
                message = "This challenge URL has expired. Please try requesting a new challenge URL."
                if endpoint == "web":
                    self.write(message)
                elif endpoint == "api":
                    self.write({"message": message})
                return
            if ip != user_challenge.get("ip"):
                # Todo: Sometimes the request from the CLI will be IPv6, and the request from browser is ipv4. How
                # can we reconcile this so that we can perform validation?
                pass
                # raise Exception("IP address used to generate challenge URL is different than IP you are using now.")
            if self.user != user_challenge.get("user"):
                log_data = {
                    **log_data,
                    "message": "Authenticated user is different then user that requested token",
                    "authenticated_user": self.user,
                    "challenge_user": user_challenge.get("user"),
                }
                log.error(log_data)
                message = (
                    "This challenge URL is associated with a different user. Ensure that your client"
                    "configuration is specifying the correct user."
                )
                if endpoint == "web":
                    self.write(message)
                elif endpoint == "api":
                    self.write({"message": message})
                return
            user_challenge["status"] = "success"
            user_challenge["user"] = self.user
            user_challenge["groups"] = self.groups
            red.hset(
                config.get("challenge_url.redis_key", "TOKEN_CHALLENGES_TEMP"),
                requested_challenge_token,
                json.dumps(user_challenge),
            )
            message = "You've successfully authenticated to ConsoleMe and may now close this page."
            if endpoint == "web":
                self.write(message)
            elif endpoint == "api":
                self.write({"message": message})
        else:
            message = "The requested challenge URL was not found. Please try requesting a new challenge URL."
            if endpoint == "web":
                self.write(message)
            elif endpoint == "api":
                self.write({"message": message})
            return


class ChallengePollerHandler(tornado.web.RequestHandler):
    """
    This endpoint is an unauthenticated endpoint that the client uses to poll for successful challenge completion.
    If the challenge has been completed successfully, and the IP of the endpoint matches the IP used to generate the
    challenge URL, we return a signed jwt. It is expected that the client will poll this endpoint continuously until
    the challenge url has been validated by a client, or until it has expired.
    """

    async def get(self, requested_challenge_token):
        if not config.get("challenge_url.enabled", False):
            raise MissingConfigurationValue(
                "Challenge URL Authentication is not enabled in ConsoleMe's configuration"
            )
        challenge_j = red.hget(
            config.get("challenge_url.redis_key", "TOKEN_CHALLENGES_TEMP"),
            requested_challenge_token,
        )
        if not challenge_j:
            self.write({"status": "unknown"})
            return
        challenge = json.loads(challenge_j)

        # Delete the token if it has expired
        current_time = int(datetime.utcnow().replace(tzinfo=pytz.UTC).timestamp())
        if challenge.get("ttl", 0) < current_time:
            red.hdel(
                config.get("challenge_url.redis_key", "TOKEN_CHALLENGES_TEMP"),
                requested_challenge_token,
            )
            self.write({"status": "expired"})
            return

        # Generate a jwt if user authentication was successful
        if challenge.get("status") == "success":
            jwt_expiration = datetime.utcnow().replace(tzinfo=pytz.UTC) + timedelta(
                minutes=config.get("jwt.expiration_minutes", 60)
            )
            encoded_jwt = await generate_jwt_token(
                challenge.get("user"), challenge.get("groups"), exp=jwt_expiration
            )

            self.write(
                {
                    "status": challenge["status"],
                    "cookie_name": config.get("auth_cookie_name", "consoleme_auth"),
                    "expiration": int(jwt_expiration.timestamp()),
                    "encoded_jwt": encoded_jwt,
                    "user": challenge["user"],
                }
            )
            # Delete the token so that it cannot be re-used
            red.hdel(
                config.get("challenge_url.redis_key", "TOKEN_CHALLENGES_TEMP"),
                requested_challenge_token,
            )
            return
        self.write({"status": challenge.get("status")})
        return

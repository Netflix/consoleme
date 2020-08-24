import uuid
from datetime import datetime, timedelta

import tornado.web
import ujson as json
from asgiref.sync import async_to_sync

from consoleme.config import config
from consoleme.exceptions.exceptions import MissingConfigurationValue
from consoleme.handlers.base import BaseHandler
from consoleme.lib.jwt import generate_jwt_token
from consoleme.lib.redis import RedisHandler

red = async_to_sync(RedisHandler().redis)()


class ChallengeGeneratorHandler(tornado.web.RequestHandler):
    """
    Challenge URLs are an alternative to mutual TLS for authenticating CLI clients of ConsoleMe.

    If Challenge Token auth is enabled, this will generate time-sensitive challenge token urls that end-users
    will be required to authenticate to. One authentication is verified, clients will be able to retrieve a
    signed jwt that clients will be able to pass to ConsoleMe for authn/authz.

    The ChallengeUrlGenerator endpoint must be unauthenticated because the CLI client will be requesting URLs
    """

    async def get(self):
        if not config.get("challenge_url.enabled", False):
            raise MissingConfigurationValue(
                "Challenge URL Authentication is not enabled in ConsoleMe's configuration"
            )
        ip = self.request.headers.get("X-Forwarded-For", self.request.remote_ip).split(
            ","
        )[0]

        # TODO: Can we rate limit this call?
        # TODO: Can we limit the UUID to the IP requesting it?
        # TODO: Logging and metrics
        token = str(uuid.uuid4())
        entry = {
            "ttl": int((datetime.utcnow() + timedelta(minutes=2)).timestamp()),
            "ip": ip,
            "status": "pending",
        }
        red.hset(config.get("challenge_url.redis_key"), token, json.dumps(entry))

        challenge_url = "{url}/challenge_validator/{token}".format(
            url=config.get("url"), token=token
        )
        polling_url = "{url}/noauth/v1/challenge_poller/{token}".format(
            url=config.get("url"), token=token
        )
        # TODO: Clean up the tokens here or somewhere else?
        self.write({"challenge_url": challenge_url, "polling_url": polling_url})


class ChallengeValidatorHandler(BaseHandler):
    """

    This is an authenticated endpoint. Once the user has authenticated successfully, we validate their information
    and return a signed jwt to the frontend.

    """

    async def get(self, requested_challenge_token):
        if not config.get("challenge_url.enabled", False):
            raise MissingConfigurationValue(
                "Challenge URL Authentication is not enabled in ConsoleMe's configuration"
            )
        ip = self.request.headers.get("X-Forwarded-For", self.request.remote_ip).split(
            ","
        )[0]
        # TODO: ttl
        # Can we force auth here?
        # self.user , self.ip, self.groups, self.eligible_roles, self.eligible_accounts
        all_challenges = red.hgetall(config.get("challenge_url.redis_key"))
        current_time = int((datetime.utcnow()).timestamp())
        expired_challenge_tokens = []
        # Delete expired tokens
        if all_challenges:
            for token, challenge_j in all_challenges.items():
                challenge = json.loads(challenge_j)
                if challenge.get("ttl", 0) < current_time:
                    expired_challenge_tokens.append(token)
            if expired_challenge_tokens:
                red.hdel(
                    config.get("challenge_url.redis_key"), *expired_challenge_tokens
                )
        else:
            raise Exception(
                "No challenge tokens were found in the cache. Did it expire?"
            )
        # Get fresh challenge for user's request
        user_challenge_j = red.hget(
            config.get("challenge_url.redis_key"), requested_challenge_token
        )
        if user_challenge_j:
            # TODO: Write errors for better debuggability
            # Do a double-take check on the ttl
            # Delete the token
            user_challenge = json.loads(user_challenge_j)
            if user_challenge.get("ttl", 0) < current_time:
                raise Exception("Challenge URL has expired")
            if ip != user_challenge.get("ip"):
                # Todo: Sometimes the request from the CLI will be IPv6, and the request from browser is ipv4. How
                # can we reconcile this so that we can perform validation?
                pass
                # raise Exception("IP address used to generate challenge URL is different than IP you are using now.")
            user_challenge["status"] = "success"
            user_challenge["user"] = self.user
            user_challenge["groups"] = self.groups
            red.hset(
                config.get("challenge_url.redis_key"),
                requested_challenge_token,
                json.dumps(user_challenge),
            )
            self.write("You've successfully authenticated and may now close this page.")
        else:
            raise Exception("Requested challenge token was not found in the cache.")


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
            config.get("challenge_url.redis_key"), requested_challenge_token
        )
        if not challenge_j:
            self.write({"status": "unknown"})
            return
        challenge = json.loads(challenge_j)
        if challenge.get("status") == "success":
            encoded_jwt = await generate_jwt_token(
                challenge.get("user"), challenge.get("groups")
            )
            self.write(
                {
                    "status": challenge["status"],
                    "cookie_name": config.get("auth_cookie_name", "consoleme_auth"),
                    "encoded_jwt": encoded_jwt.decode("utf-8"),
                }
            )
            red.hdel(config.get("challenge_url.redis_key"), requested_challenge_token)
            return
        self.write({"status": challenge.get("status")})
        return

from datetime import datetime

import pytz
import ujson as json
from asgiref.sync import async_to_sync

from consoleme.config import config
from consoleme.lib.redis import RedisHandler

log = config.get_logger()
red = async_to_sync(RedisHandler().redis)()


async def delete_expired_challenges(all_challenges):
    current_time = int(datetime.utcnow().replace(tzinfo=pytz.UTC).timestamp())
    expired_challenge_tokens = []
    for token, challenge_j in all_challenges.items():
        challenge = json.loads(challenge_j)
        if challenge.get("ttl", 0) < current_time:
            expired_challenge_tokens.append(token)
    if expired_challenge_tokens:
        red.hdel(
            config.get("challenge_url.redis_key", "TOKEN_CHALLENGES_TEMP"),
            *expired_challenge_tokens,
        )


async def retrieve_user_challenge(request, requested_challenge_token, log_data):
    current_time = int(datetime.utcnow().replace(tzinfo=pytz.UTC).timestamp())
    # Get fresh challenge for user's request
    user_challenge_j = red.hget(
        config.get("challenge_url.redis_key", "TOKEN_CHALLENGES_TEMP"),
        requested_challenge_token,
    )
    if not user_challenge_j:
        message = "The requested challenge URL was not found. Please try requesting a new challenge URL."
        request.write({"message": message})
        return
    # Do a double-take check on the ttl
    # Delete the token
    user_challenge = json.loads(user_challenge_j)
    if user_challenge.get("ttl", 0) < current_time:
        message = (
            "This challenge URL has expired. Please try requesting a new challenge URL."
        )
        request.write({"message": message})
        return
    if request.user != user_challenge.get("user"):
        log_data = {
            **log_data,
            "message": "Authenticated user is different then user that requested token",
            "authenticated_user": request.user,
            "challenge_user": user_challenge.get("user"),
        }
        log.error(log_data)
        message = (
            "This challenge URL is associated with a different user. Ensure that your client "
            "configuration is specifying the correct user."
        )
        request.write({"message": message})
        return
    return user_challenge

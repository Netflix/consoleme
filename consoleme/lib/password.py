import asyncio
from typing import Dict, List, Optional, Union

from password_strength import PasswordPolicy

from consoleme.config import config
from consoleme.lib.redis import RedisHandler

red = RedisHandler().redis_sync()


async def wait_after_authentication_failure(user) -> str:
    redix_key_expiration = config.get(
        "wait_after_authentication_failure.expiration", 60
    )
    redis_key = f"wait_after_authentication_failure_{user}"
    num_password_failures = red.get(redis_key)
    if not num_password_failures:
        num_password_failures = 0
    num_password_failures = int(num_password_failures)  # Redis values are strings
    red.setex(redis_key, redix_key_expiration, num_password_failures + 1)
    await asyncio.sleep(num_password_failures ** 2)
    next_delay = (num_password_failures + 1) ** 2
    return (
        f"Your next authentication failure will result in a {next_delay} second wait. "
        f"This wait time will expire after {redix_key_expiration} seconds of no authentication failures."
    )


async def check_password_strength(
    password,
) -> Optional[Union[Dict[str, str], Dict[str, List[str]]]]:
    password_policy_args = {
        "strength": config.get("auth.password_policy.strength", 0.5),
        "entropy_bits": config.get("auth.password_policy.entry_bits"),
        "length": config.get("auth.password_policy.length"),
        "uppercase": config.get("auth.password_policy.uppercase"),
        "numbers": config.get("auth.password_policy.numbers"),
        "special": config.get("auth.password_policy.special"),
        "nonletters": config.get("auth.password_policy.nonletters"),
    }

    # We remove entries with null values since password_strength doesn't like them.
    password_policy_args = {k: v for k, v in password_policy_args.items() if v}

    policy = PasswordPolicy.from_names(**password_policy_args)

    tested_pass = policy.password(password)
    errors = tested_pass.test()
    # Convert errors to string so they can be json encoded later
    errors: List[str] = [str(e) for e in errors]

    if errors:
        return {"message": "Password doesn't have enough entropy.", "errors": errors}

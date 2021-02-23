from typing import Dict, List, Optional, Union

from password_strength import PasswordPolicy

from consoleme.config import config


async def check_password_stength(
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

import sys

from consoleme.config import config
from consoleme.lib.plugins import get_plugin_by_name

aws = get_plugin_by_name(config.get("plugins.aws"))()
stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()

# ALL ACCOUNTS is a dictionary of account ID to a list of account names (including aliases)
# ex: {"123456": ["account_name", "account_alias_1",...], ...}
ALL_ACCOUNTS = aws.get_account_ids_to_names()

# We only want to consider the primary (first) account name in the list for the purposes of displaying them to the user
for k, v in ALL_ACCOUNTS.items():
    ALL_ACCOUNTS[k] = v[0]


def format_role_name(arn: str, accounts: dict) -> str:
    """Given a role name, return what to display on the UI. This cleanly formats per-user roles."""
    role_name = arn.split("role/")[1]
    if not accounts:
        # Only fall back to ALL_ACCOUNTS if an accounts dict is not supplied
        accounts = ALL_ACCOUNTS

    if config.get("format_role_name.show_full_arn"):
        return arn
    elif config.get("format_role_name.show_account_name_role_name"):
        account_id = arn.split(":")[4]
        account_name = accounts.get(account_id)
        if not account_name:
            account_name = account_id
        return f"{account_name}/{role_name}"

    if not role_name.startswith("cm_"):
        return role_name

    name = accounts.get(arn.split(":")[4])

    # This should NOT happen, but if it does, log it keep a metric of it:
    if not name:
        log_data = {
            "function": f"{__name__}.{sys._getframe().f_code.co_name}",
            "message": "Can't find account for per-user role",
            "role": role_name,
            "accounts": accounts,
        }
        log.error(log_data)

        stats.count("index.unknown_account_role", tags={"role": role_name})

    return name

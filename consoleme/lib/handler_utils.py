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
    """Given a role name, return what to display on the UI. This cleanly formats the per-user roles."""
    # TODO: Allow this to be configured to just return arn?
    role = arn.split("role/")[1]
    if not role.startswith("cm_"):
        return role

    if not accounts:
        # Only fall back to ALL_ACCOUNTS if an accounts dict is not supplied
        accounts = ALL_ACCOUNTS

    name = accounts.get(arn.split(":")[4])

    # This should NOT happen, but if it does, log it keep a metric of it:
    if not name:
        log_data = {
            "function": f"{__name__}.{sys._getframe().f_code.co_name}",
            "message": "Can't find account for per-user role",
            "role": role,
            "accounts": accounts,
        }
        log.error(log_data)

        stats.count("index.unknown_account_role", tags={"role": role})

    return name

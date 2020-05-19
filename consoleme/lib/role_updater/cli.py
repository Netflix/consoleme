import getpass
import platform

import click
import click_log
import ujson as json
from asgiref.sync import async_to_sync

from consoleme.lib.role_updater.handler import log
from consoleme.lib.role_updater.handler import update_role as update_role_handler

click_log.basic_config(log)


@click.group()
@click_log.simple_verbosity_option(log)
def cli():
    log.debug("Running...")
    print("RUNNING")


def get_session_name():
    """Set a session name if running locally."""
    if platform.platform().lower().startswith("darwin"):
        session_name = getpass.getuser()
        return session_name

    return "roleupdater"


@cli.command()
@click.option("--event", type=str, help="Event json string", required=True)
def update_role(event):
    """Update a role policy"""

    with open(event, "r") as f:
        event_data = json.load(f)

    for e in event_data:
        e["requestor"] = e["requestor"].format(requestor=get_session_name())

    result = async_to_sync(update_role_handler)(event_data, None)

    if result.get("success", False):
        log.info("Role policy update successful")
    else:
        log.info("Role policy update failed")


if __name__ == "__main__":
    cli()

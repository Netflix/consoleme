"""
This module controls defines internal-only celery tasks and their applicable schedules. These will be combined with
the external tasks

"""
import json
from datetime import timedelta

from asgiref.sync import async_to_sync
from celery import Celery

from consoleme.config import config
from consoleme.lib.json_encoder import SetEncoder
from consoleme.lib.redis import RedisHandler

region = config.region
red = async_to_sync(RedisHandler().redis)()

app = Celery(
    "tasks",
    broker=config.get("celery.broker.{}".format(region), "redis://127.0.0.1:6379/1"),
)

if config.get("celery.purge"):
    app.control.purge()


@app.task(soft_time_limit=600)
def cache_application_information():
    """
    This task retrieves application information from configuration. You may want to override this function to
    utilize your organization's CI/CD pipeline for this information.
    :return:
    """
    apps_to_roles = {}
    for k, v in config.get("application_settings", {}).items():
        apps_to_roles[k] = v.get("roles", [])

    red.set(
        config.get("celery.apps_to_roles.redis_key", "APPS_TO_ROLES"),
        json.dumps(apps_to_roles, cls=SetEncoder),
    )


@app.task
def task_1():
    """
    This task demonstrates how you can implement your own internal celery tasks to run on schedule or on demand.
    :return:
    """
    pass


schedule = timedelta(seconds=1800)

internal_schedule = {
    "task1": {
        "task": "consoleme_default_plugins.plugins.celery_tasks.celery_tasks.task_1",
        "options": {"expires": 4000},
        "schedule": schedule,
    },
    "cache_application_information": {
        "task": "consoleme_default_plugins.plugins.celery_tasks.celery_tasks.cache_application_information",
        "options": {"expires": 4000},
        "schedule": schedule,
    },
}


def init():
    """Initialize the Celery Tasks plugin."""
    return internal_schedule

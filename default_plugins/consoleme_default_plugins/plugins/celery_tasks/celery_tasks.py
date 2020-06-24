"""
This module controls defines internal-only celery tasks and their applicable schedules. These will be combined with
the external tasks

"""
from datetime import timedelta

from celery import Celery

from consoleme.config import config

region = config.region

app = Celery(
    "tasks",
    broker=config.get("celery.broker.{}".format(region), "redis://127.0.0.1:6379/1"),
)

if config.get("celery.purge"):
    app.control.purge()


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
    }
}


def init():
    """Initialize the Celery Tasks plugin."""
    return internal_schedule

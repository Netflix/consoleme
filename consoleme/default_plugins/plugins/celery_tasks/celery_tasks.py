"""
This module controls defines internal-only celery tasks and their applicable schedules. These will be combined with
the external tasks

"""
import json
import os
from datetime import timedelta

from asgiref.sync import async_to_sync
from celery import Celery

from consoleme.config import config
from consoleme.lib.json_encoder import SetEncoder
from consoleme.lib.redis import RedisHandler
from consoleme.lib.timeout import Timeout

region = config.region
red = async_to_sync(RedisHandler().redis)()

app = Celery(
    "tasks",
    broker=config.get(
        f"celery.broker.{config.region}",
        config.get("celery.broker.global", "redis://127.0.0.1:6379/1"),
    ),
    backend=config.get(
        f"celery.backend.{config.region}",
        config.get("celery.broker.global", "redis://127.0.0.1:6379/2"),
    ),
)

if config.get("redis.use_redislite"):
    import tempfile

    import redislite

    redislite_db_path = os.path.join(
        config.get("redis.redislite.db_path", tempfile.NamedTemporaryFile().name)
    )
    redislite_client = redislite.Redis(redislite_db_path)
    redislite_socket_path = f"redis+socket://{redislite_client.socket_file}"
    app = Celery(
        "tasks",
        broker=f"{redislite_socket_path}?virtual_host=1",
        backend=f"{redislite_socket_path}?virtual_host=2",
    )

app.conf.result_expires = config.get("celery.result_expires", 60)
app.conf.worker_prefetch_multiplier = config.get("celery.worker_prefetch_multiplier", 4)
app.conf.task_acks_late = config.get("celery.task_acks_late", True)

if config.get("celery.purge") and not config.get("redis.use_redislite"):
    # Useful to clear celery queue in development
    with Timeout(seconds=5, error_message="Timeout: Are you sure Redis is running?"):
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
        "task": "consoleme.default_plugins.plugins.celery_tasks.celery_tasks.task_1",
        "options": {"expires": 4000},
        "schedule": schedule,
    },
    "cache_application_information": {
        "task": "consoleme.default_plugins.plugins.celery_tasks.celery_tasks.cache_application_information",
        "options": {"expires": 4000},
        "schedule": schedule,
    },
}


def init():
    """Initialize the Celery Tasks plugin."""
    return internal_schedule

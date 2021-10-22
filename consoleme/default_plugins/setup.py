"""
example_consoleme_plugins
==============

This is an example setup configuration for ConsoleMe plugins. You can get
started writing your own plugins by copying this directory (default_plugins)
and customizing it for your needs. Be sure to update the "default_*" entrypoint
names below.

Overview of steps:
1. Copy default_plugins directory to your desired location
2. Change to new default_plugins directory
3. Delete __init__.py
4. Modify plugins to your liking
5. Update the entrypoints in setup.py, e.g. default_config -> my_custom_config
6. Update your configuration to use the new plugin entrypoints
"""
from setuptools import find_packages, setup

setup(
    name="example_consoleme_plugins",
    version="0.0.1",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    setup_requires=["setupmeta"],
    python_requires=">=3.8",
    entry_points={
        "consoleme.plugins": [
            # Change the name of the entry point for your plugin here, and in your configuration
            "default_config = example_consoleme_plugins.plugins.config.config:Config",
            "default_auth = example_consoleme_plugins.plugins.auth.auth:Auth",
            "default_aws = example_consoleme_plugins.plugins.aws.aws:Aws",
            "default_celery_tasks = example_consoleme_plugins.plugins.celery_tasks.celery_tasks:internal_schedule",
            "default_celery_tasks_functions = example_consoleme_plugins.plugins.celery_tasks.celery_tasks:CeleryTasks",
            "default_metrics = example_consoleme_plugins.plugins.metrics.metrics:Metric",
            "default_policies = example_consoleme_plugins.plugins.policies.policies:Policies",
            "default_group_mapping = example_consoleme_plugins.plugins.group_mapping.group_mapping:GroupMapping",
            "default_internal_routes = example_consoleme_plugins.plugins.internal_routes.internal_routes:InternalRoutes",
        ]
    },
)

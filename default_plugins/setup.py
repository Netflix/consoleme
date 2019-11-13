"""
consoleme_default_plugins
==============

Default plugins for ConsoleMe

"""
import distutils.cmd
import distutils.log
import distutils.cmd
import distutils.log
import os
from shutil import rmtree

from setuptools import setup, find_packages


class CleanAllCommand(distutils.cmd.Command):
    """Docstring for public class."""

    description = "remove extra build files"
    user_options = []
    dirname = os.path.dirname(os.path.realpath(__file__))

    def initialize_options(self):
        """Docstring for public method."""
        pass

    def finalize_options(self):
        """Docstring for public method."""
        pass

    def run(self):
        """Docstring for public method."""
        targets = [
            ".cache",
            ".coverage.py27",
            ".coverage.py36",
            ".tox",
            "coverage-html.py27",
            "coverage-html.py36",
            "consoleme.egg-info",
            "consoleme/__pycache__",
            "test/__pycache__",
        ]
        for t in targets:
            path = os.path.join(self.dirname, t)
            if os.path.isfile(path):
                self.announce(
                    "removing file: {}".format(path), level=distutils.log.INFO
                )
                os.remove(path)
            elif os.path.isdir(path):
                self.announce(
                    "removing directory: {}".format(path), level=distutils.log.INFO
                )
                rmtree(path)


install_requires = []

setup(
    name="consoleme_default_plugins",
    version="0.1",
    author="Curtis Castrapel",
    author_email="ccastrapel@netflix.com",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    setup_requires=["setupmeta"],
    python_requires=">=3.7",
    entry_points={
        "consoleme.plugins": [
            # Change the name of the entry point for your plugin here, and in your configuration
            "default_config = consoleme_default_plugins.plugins.config.config:Config",
            "default_auth = consoleme_default_plugins.plugins.auth.auth:Auth",
            "default_aws = consoleme_default_plugins.plugins.aws.aws:Aws",
            "default_celery_tasks = consoleme_default_plugins.plugins.celery_tasks.celery_tasks:internal_schedule",
            "default_celery_tasks_functions = consoleme_default_plugins.plugins.celery_tasks.celery_tasks:CeleryTasks",
            "default_metrics = consoleme_default_plugins.plugins.metrics.metrics:Metric",
            "default_group_mapping = consoleme_default_plugins.plugins.group_mapping.group_mapping:GroupMapping",
            "default_internal_routes = consoleme_default_plugins.plugins.internal_routes.internal_routes:InternalRoutes",
        ]
    },
    cmdclass={"cleanall": CleanAllCommand},
)

import os
from shutil import rmtree

import distutils.cmd
import distutils.log
from setuptools import find_packages, setup


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
                self.announce(f"removing file: {path}", level=distutils.log.INFO)
                os.remove(path)
            elif os.path.isdir(path):
                self.announce(f"removing directory: {path}", level=distutils.log.INFO)
                rmtree(path)


setup(
    name="consoleme",
    author="Netflix Security",
    author_email="consoleme-maintainers@netflix.com",
    description="A central control plane for AWS permissions and access",
    keywords="consoleme",
    url="https://github.com/Netflix/ConsoleMe",
    python_requires=">=3.8",
    setup_requires=["setupmeta"],
    packages=find_packages(exclude=("tests",)),
    entry_points={
        "console_scripts": [
            "consoleme = consoleme.__main__:init",
        ],
        "consoleme.plugins": [
            "default_config = consoleme.default_plugins.plugins.config.config:Config",
            "default_auth = consoleme.default_plugins.plugins.auth.auth:Auth",
            "default_aws = consoleme.default_plugins.plugins.aws.aws:Aws",
            "default_celery_tasks = consoleme.default_plugins.plugins.celery_tasks.celery_tasks:internal_schedule",
            "default_celery_tasks_functions = consoleme.default_plugins.plugins.celery_tasks.celery_tasks:CeleryTasks",
            "default_metrics = consoleme.default_plugins.plugins.metrics.metrics:Metric",
            "default_policies = consoleme.default_plugins.plugins.policies.policies:Policies",
            "default_group_mapping = consoleme.default_plugins.plugins.group_mapping.group_mapping:GroupMapping",
            "default_internal_routes = consoleme.default_plugins.plugins.internal_routes.internal_routes:InternalRoutes",
        ],
    },
    cmdclass={"cleanall": CleanAllCommand},
    include_package_data=True,
    versioning="dev",
    zip_safe=False,
)

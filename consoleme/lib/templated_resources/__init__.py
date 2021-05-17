import os
import tempfile
from typing import List, Optional

import sentry_sdk
from asgiref.sync import async_to_sync
from pydantic import BaseModel
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap as OrderedDict

from consoleme.config import config
from consoleme.lib.git import clone_repo
from consoleme.lib.pydantic import BaseModel
from consoleme.lib.templated_resources.models import (
    TemplatedResourceModelArray,
    TemplateFile,
)

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.width = 4096


async def cache_resource_templates():
    for repository in config.get("cache_resource_templates.repositories", []):
        if repository.get("type") == "git":
            await cache_resource_templates_for_repository(repository)


async def cache_resource_templates_for_repository(
    repository,
) -> TemplatedResourceModelArray:
    if repository["type"] not in ["git"]:
        raise Exception("Unsupported repository type")
    tempdir = tempfile.mkdtemp()
    repo_url = repository["repo_url"]
    repo = clone_repo(repo_url, tempdir)
    repo.config_writer().set_value("user", "name", "ConsoleMe").release()
    email = repository["authentication_settings"]["email"]
    resource_formats = repository["resource_formats"]
    discovered_templates = []
    if email:
        repo.config_writer().set_value("user", "email", email).release()
    for subdir, dirs, files in os.walk(repo.working_dir):
        for filename in files:
            template_matched = False
            subdir = subdir.replace(tempdir + os.sep, "")
            filepath = subdir + os.sep + filename
            relative_path = "/".join(subdir.split("/")[1:]) + os.sep + filename
            web_path = repository.get("web_path", "").format(
                relative_path=relative_path
            )
            full_temporary_file_path = tempdir + "/" + filepath
            if "honeybee" in resource_formats:
                for resource_type, conditions in repository["resource_type_parser"][
                    "honeybee"
                ].items():
                    if template_matched:
                        continue
                    for condition in conditions:
                        if condition.get("path_prefix") and not filepath.startswith(
                            condition["path_prefix"]
                        ):
                            continue
                        if condition.get("path_suffix") and not filepath.endswith(
                            condition["path_suffix"]
                        ):
                            continue
                        with open(full_temporary_file_path, "r") as f:
                            try:
                                file_content = yaml.load(f)
                            except Exception:
                                sentry_sdk.capture_exception()
                                # TODO LOG HERE
                                continue
                        name = file_content.get("Name")
                        owner = file_content.get("Owner")
                        include_accounts = file_content.get("IncludeAccounts")
                        exclude_accounts = file_content.get("ExcludeAccounts")
                        if condition.get("file_content"):
                            should_ignore_file = False
                            body_should_include = condition["file_content"].get(
                                "includes", []
                            )
                            body_should_exclude = condition["file_content"].get(
                                "excludes", []
                            )
                            for include in body_should_include:
                                if include not in file_content:
                                    should_ignore_file = True
                                    break
                            for exclude in body_should_exclude:
                                if exclude in file_content:
                                    should_ignore_file = True
                            if should_ignore_file:
                                continue
                        # with open(filepath, "r") as f:
                        # TODO: read YAML and figure out name, owner, accounts, etc
                        discovered_templates.append(
                            TemplateFile(
                                name=name,
                                owner=owner,
                                include_accounts=include_accounts,
                                exclude_accounts=exclude_accounts,
                                resource=relative_path,
                                file_path=filepath,
                                web_path=web_path,
                                resource_type=resource_type,
                                template_language="honeybee",
                            )
                        )
                        template_matched = True
                        break
    print(discovered_templates)
    # TODO: Save this to S3


async_to_sync(cache_resource_templates)()

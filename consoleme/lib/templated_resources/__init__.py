import fnmatch
import os
import sys
import tempfile
from typing import Optional, Union

import sentry_sdk
from ruamel.yaml import YAML

from consoleme.config import config
from consoleme.lib.account_indexers import get_account_id_to_name_mapping
from consoleme.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from consoleme.lib.git import clone_repo
from consoleme.lib.templated_resources.models import (
    TemplatedFileModelArray,
    TemplateFile,
)

log = config.get_logger()

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.width = 4096


async def cache_resource_templates() -> TemplatedFileModelArray:
    templated_file_array = TemplatedFileModelArray(templated_resources=[])
    for repository in config.get("cache_resource_templates.repositories", []):
        if repository.get("type") == "git":
            result = await cache_resource_templates_for_repository(repository)
            templated_file_array.templated_resources.extend(result.templated_resources)
    await store_json_results_in_redis_and_s3(
        templated_file_array.dict(),
        redis_key=config.get(
            "cache_resource_templates.redis.key", "cache_templated_resources_v1"
        ),
        s3_bucket=config.get("cache_resource_templates.s3.bucket"),
        s3_key=config.get(
            "cache_resource_templates.s3.file",
            "cache_templated_resources/cache_templated_resources_v1.json.gz",
        ),
    )
    return templated_file_array


async def retrieve_cached_resource_templates(
    resource_type: Optional[str] = None,
    resource: Optional[str] = None,
    repository_name: Optional[str] = None,
    template_language: Optional[str] = None,
    return_first_result=False,
) -> Optional[Union[TemplatedFileModelArray, TemplateFile]]:
    matching_templates = []
    templated_resource_data_d = await retrieve_json_data_from_redis_or_s3(
        redis_key=config.get(
            "cache_resource_templates.redis.key", "cache_templated_resources_v1"
        ),
        s3_bucket=config.get("cache_resource_templates.s3.bucket"),
        s3_key=config.get(
            "cache_resource_templates.s3.file",
            "cache_templated_resources/cache_templated_resources_v1.json.gz",
        ),
    )
    templated_file_array = TemplatedFileModelArray.parse_obj(templated_resource_data_d)
    for template_file in templated_file_array.templated_resources:
        if resource_type and not template_file.resource_type == resource_type:
            continue
        if resource and not template_file.resource == resource:
            continue
        if repository_name and not template_file.repository_name == repository_name:
            continue
        if (
            template_language
            and not template_file.template_language == template_language
        ):
            continue
        if return_first_result:
            return template_file
        matching_templates.append(template_file)
    if return_first_result:
        return None
    return TemplatedFileModelArray(templated_resources=matching_templates)


async def cache_resource_templates_for_repository(
    repository,
) -> TemplatedFileModelArray:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {
        "function": function,
        "repository": repository,
    }
    if repository["type"] not in ["git"]:
        raise Exception("Unsupported repository type")
    tempdir = tempfile.mkdtemp()
    repo_url = repository["repo_url"]
    repo = clone_repo(repo_url, tempdir)
    repo.config_writer().set_value("user", "name", "ConsoleMe").release()
    email = repository["authentication_settings"]["email"]
    resource_formats = repository["resource_formats"]
    discovered_templates = []
    accounts_d = await get_account_id_to_name_mapping()
    accounts_set = set(accounts_d.values())
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
                            except Exception as e:
                                sentry_sdk.capture_exception()
                                log.error(
                                    {
                                        **log_data,
                                        "Message": "Error trying to parse template",
                                        "file_path": full_temporary_file_path,
                                        "error": str(e),
                                    },
                                    exc_info=True,
                                )
                                continue
                        name = file_content.get(
                            "TemplateName", file_content.get("Name", filename)
                        )
                        owner = file_content.get("Owner")

                        # Generate a set of accounts the template applies to. This is used to get the number of accounts
                        # affected by a resource template.
                        included_accounts_set = set()
                        include_accounts = file_content.get("IncludeAccounts", [])
                        if include_accounts:
                            for include_account in include_accounts:
                                for account in accounts_set:
                                    if fnmatch.fnmatch(account, include_account):
                                        included_accounts_set.add(account)
                        exclude_accounts = file_content.get("ExcludeAccounts", [])
                        if exclude_accounts:
                            for exclude_account in exclude_accounts:
                                for account in accounts_set:
                                    if fnmatch.fnmatch(account, exclude_account):
                                        if account not in included_accounts_set:
                                            continue
                                        included_accounts_set.remove(account)

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

                        discovered_templates.append(
                            TemplateFile(
                                name=name,
                                repository_name=repository["name"],
                                owner=owner,
                                include_accounts=include_accounts,
                                exclude_accounts=exclude_accounts,
                                number_of_accounts=len(included_accounts_set),
                                resource=relative_path,
                                file_path=filepath,
                                web_path=web_path,
                                resource_type=resource_type,
                                template_language="honeybee",
                            )
                        )
                        template_matched = True
                        break
    return TemplatedFileModelArray(templated_resources=discovered_templates)

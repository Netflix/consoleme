import os
import shutil
import tempfile
from pathlib import Path

import git
import sentry_sdk
from asgiref.sync import async_to_sync
from ruamel.yaml import YAML

from consoleme.config import config
from consoleme.lib.account_indexers import get_account_id_to_name_mapping


def clone_repo(git_url: str, tempdir) -> git.Repo:
    """Clone the honeybee-templates repo to an ephemeral directory and return the git.Repo reference."""
    git.Git(tempdir).clone(git_url)
    return git.Repo(os.path.join(tempdir, git_url.split("/")[-1].replace(".git", "")))


def sort_dict(original):
    """Recursively sorts dictionary keys and dictionary values in alphabetical order"""
    if isinstance(original, dict):
        res = (
            dict()
        )  # Make a new "ordered" dictionary. No need for Collections in Python 3.7+
        for k, v in sorted(original.items()):
            res[k] = v
        d = res
    else:
        d = original
    for k in d:
        if isinstance(d[k], str):
            continue
        if isinstance(d[k], list) and len(d[k]) > 1 and isinstance(d[k][0], str):
            d[k] = sorted(d[k])
        if isinstance(d[k], dict):
            d[k] = sort_dict(d[k])
        if isinstance(d[k], list) and len(d[k]) >= 1 and isinstance(d[k][0], dict):
            for i in range(len(d[k])):
                d[k][i] = sort_dict(d[k][i])
    return d


def store_iam_resources_in_git(
    iam_resources,
    account_id,
    git_url=config.get("cache_iam_resources_for_account.store_in_git.repo"),
    git_message="[Automated] Update IAM Cache",
):
    accounts_d = async_to_sync(get_account_id_to_name_mapping)()
    tempdir = tempfile.mkdtemp()
    try:
        repo = clone_repo(git_url, tempdir)

        expected_entries = {
            "UserDetailList": {
                "category": "iam_users",
                "resource_name_key": "UserName",
            },
            "GroupDetailList": {
                "category": "iam_groups",
                "resource_name_key": "GroupName",
            },
            "RoleDetailList": {
                "category": "iam_roles",
                "resource_name_key": "RoleName",
            },
            "Policies": {"category": "iam_policies", "resource_name_key": "PolicyName"},
        }

        for key, settings in expected_entries.items():
            category = settings["category"]
            for resource in iam_resources[key]:
                if key == "RoleDetailList":
                    resource.pop("RoleLastUsed", None)
                resource_name = resource[settings["resource_name_key"]]
                yaml = YAML()
                yaml.preserve_quotes = True  # type: ignore
                yaml.indent(mapping=2, sequence=4, offset=2)

                account_name = accounts_d.get(account_id, account_id)
                if not account_name:
                    account_name = "unknown"
                path_in_repo = os.path.join(
                    repo.working_dir, f"{account_name}/{category}/{resource_name}.yaml"
                )
                os.makedirs(Path(path_in_repo).parent.absolute(), exist_ok=True)

                with open(path_in_repo, "w") as f:
                    yaml.dump(sort_dict(resource), f)
        repo.git.add("*")
        if repo.index.diff("HEAD"):
            repo.index.commit(git_message)
            origin = repo.remote("origin")
            origin.pull()
            origin.push("master", force=True)
    except Exception:  # noqa
        sentry_sdk.capture_exception()
    shutil.rmtree(tempdir)

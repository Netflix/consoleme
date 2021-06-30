import os
import shutil
import tempfile
from pathlib import Path

import sentry_sdk
import yaml as builtin_yaml
from asgiref.sync import async_to_sync
from deepdiff import DeepDiff
from ruamel.yaml import YAML

from consoleme.config import config
from consoleme.lib.account_indexers import get_account_id_to_name_mapping
from consoleme.lib.generic import sort_dict


def clone_repo(git_url: str, tempdir):
    import git

    """Clone the honeybee-templates repo to an ephemeral directory and return the git.Repo reference."""
    git.Git(tempdir).clone(git_url)
    return git.Repo(os.path.join(tempdir, git_url.split("/")[-1].replace(".git", "")))


def store_iam_resources_in_git(
    iam_resources,
    account_id,
    git_url=config.get("cache_iam_resources_for_account.store_in_git.repo"),
    git_message="[Automated] Update IAM Cache",
):
    """
    Experimental function to force-push discovered IAM resources into a Git repository's master branch.
    Use at your own risk.
    """
    accounts_d = async_to_sync(get_account_id_to_name_mapping)()
    tempdir = tempfile.mkdtemp()
    try:
        repo = clone_repo(git_url, tempdir)
        repo.config_writer().set_value("user", "name", "ConsoleMe").release()
        email = config.get("cache_iam_resources_for_account.store_in_git.email")
        if email:
            repo.config_writer().set_value("user", "email", email).release()

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

                should_write = True
                to_write = sort_dict(resource)
                if os.path.exists(path_in_repo):
                    with open(path_in_repo, "r") as f:
                        # Unfortunately at the time of writing, ruamel.yaml loads this into ordered dictionaries.
                        # We want this to be the same type as `to_write`, so we use the builtin yaml library to load it
                        existing = builtin_yaml.safe_load(f)
                    if not DeepDiff(to_write, existing, ignore_order=True):
                        should_write = False
                if should_write:
                    with open(path_in_repo, "w") as f:
                        yaml.dump(to_write, f)
        repo.git.add("*")
        if repo.index.diff("HEAD"):
            repo.index.commit(git_message)
            origin = repo.remote("origin")
            origin.pull()
            origin.push("master", force=True)
    except Exception:  # noqa
        sentry_sdk.capture_exception()
    shutil.rmtree(tempdir)

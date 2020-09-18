import os
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import git
from asgiref.sync import async_to_sync
from ruamel.yaml import YAML

from consoleme.config import config
from consoleme.lib.account_indexers import get_account_id_to_name_mapping


def clone_repo(git_url: str, tempdir) -> git.Repo:
    """Clone the honeybee-templates repo to an ephemeral directory and return the git.Repo reference."""
    git.Git(tempdir).clone(git_url)
    return git.Repo(os.path.join(tempdir, git_url.split("/")[-1].replace(".git", "")))


def store_iam_resources_in_git(
    iam_resources,
    account_id,
    git_url=config.get("cache_iam_resources_for_account.store_in_git.repo"),
    git_message="[Automated] Update IAM Cache",
):
    accounts_d = async_to_sync(get_account_id_to_name_mapping)()
    tempdir = tempfile.mkdtemp()
    repo = clone_repo(git_url, tempdir)

    expected_entries = {
        "UserDetailList": {"category": "iam_users", "resource_name_key": "UserName"},
        "GroupDetailList": {"category": "iam_groups", "resource_name_key": "GroupName"},
        "RoleDetailList": {"category": "iam_roles", "resource_name_key": "RoleName"},
        "Policies": {"category": "iam_policies", "resource_name_key": "PolicyName"},
    }
    ttl: int = int((datetime.utcnow() + timedelta(hours=36)).timestamp())
    current_time: int = int((datetime.utcnow() + timedelta(hours=36)).timestamp())

    for key, settings in expected_entries.items():
        category = settings["category"]
        for resource in iam_resources[key]:
            # set a TTL to key on for deletion
            resource["ttl"] = ttl
            resource["last_updated"] = current_time
            resource_name = resource[settings["resource_name_key"]]
            arn = resource["Arn"]
            yaml = YAML()
            yaml.preserve_quotes = True  # type: ignore
            yaml.indent(mapping=2, sequence=4, offset=2)

            account_id = arn.split(":")[4] or account_id
            account_name = accounts_d.get(account_id, account_id)
            if not account_name:
                account_name = "unknown"
            path_in_repo = os.path.join(
                repo.working_dir, f"{account_name}/{category}/{resource_name}.yaml"
            )
            os.makedirs(Path(path_in_repo).parent.absolute(), exist_ok=True)

            with open(path_in_repo, "w") as f:
                yaml.dump(resource, f)
    repo.git.add("*")
    repo.index.commit(git_message)
    origin = repo.remote("origin")
    origin.pull()
    origin.push("master", force=True)
    shutil.rmtree(tempdir)

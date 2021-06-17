import io
import json
import os
import tempfile
import time
from typing import Optional

import git
from asgiref.sync import sync_to_async
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq

from consoleme.config import config
from consoleme.lib.aws import minimize_iam_policy_statements
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.models import (
    ChangeModelArray,
    ExtendedRequestModel,
    GenericFileChangeModel,
    RequestCreationModel,
    RequestStatus,
    UserModel,
)

auth = get_plugin_by_name(config.get("plugins.auth", "default_auth"))()

typ = "rt"
yaml = YAML(typ=typ)
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.representer.ignore_aliases = lambda *data: True
yaml.width = 4096


class GitRepository:
    def __init__(self, repo_url, repo_name):
        self.repo_url = repo_url
        self.repo = None
        self.repo_name = repo_name
        self.git = None

    async def clone(self, no_checkout=True, depth: Optional[int] = None):
        args = []
        kwargs = {}
        if no_checkout:
            args.append("-n")
        args.append(self.repo_url)
        if depth:
            kwargs["depth"] = depth
        tempdir = tempfile.mkdtemp()
        await sync_to_async(git.Git(tempdir).clone)(*args, **kwargs)
        self.repo = git.Repo(os.path.join(tempdir, self.repo_name))
        self.git = self.repo.git
        return self.repo


async def generate_honeybee_request_from_change_model_array(
    request_creation: RequestCreationModel, user: str
) -> ExtendedRequestModel:
    repositories_for_request = {}
    primary_principal = None
    t = int(time.time())
    generated_branch_name = f"{user}-{t}"
    policy_name = config.get(
        "generate_honeybee_request_from_change_model_array.policy_name",
        "self_service_generated",
    )
    # Checkout Git Repo and generate a branch name for the user's change
    for change in request_creation.changes.changes:
        if primary_principal and change.principal != primary_principal:
            raise Exception("Changes must all affect the same principal")
        primary_principal = change.principal
        discovered_repository_for_change = False
        if repositories_for_request.get(change.principal.repository_name):
            continue
        # 1. Find repo
        for r in config.get("cache_resource_templates.repositories", []):
            if r["name"] == change.principal.repository_name:
                repo = GitRepository(r["repo_url"], r["name"])
                await repo.clone(depth=1)
                git_client = repo.git
                git_client.reset()
                git_client.checkout(b=generated_branch_name)
                repositories_for_request[change.principal.repository_name] = {
                    "main_branch_name": r["main_branch_name"],
                    "repo": repo.repo,
                    "git_client": git_client,
                }
                discovered_repository_for_change = True
                break
        if not discovered_repository_for_change:
            raise Exception(
                "No matching repository found for change in ConsoleMe's configuration"
            )
    request_changes = ChangeModelArray(changes=[])
    for change in request_creation.changes.changes:
        git_client = repositories_for_request[change.principal.repository_name][
            "git_client"
        ]
        repo = repositories_for_request[change.principal.repository_name]["repo"]
        main_branch_name = repositories_for_request[change.principal.repository_name][
            "main_branch_name"
        ]
        git_client.checkout(
            f"origin/{main_branch_name}", change.principal.resource_identifier
        )
        with open(
            f"{repo.working_dir}/{change.principal.resource_identifier}", "r"
        ) as f:
            yaml_content = yaml.load(f)

        # Original
        buf = io.BytesIO()
        yaml.dump(yaml_content, buf)
        original_text = buf.getvalue()
        successfully_merged_statement = False
        if not yaml_content.get("Policies"):
            yaml_content["Policies"] = []
        if isinstance(yaml_content["Policies"], dict):
            yaml_content["Policies"] = [yaml_content["Policies"]]

        if isinstance(change.policy.policy_document["Statement"], str):
            change.policy.policy_document["Statement"] = [
                change.policy.policy_document["Statement"]
            ]
        for i in range(len(yaml_content.get("Policies", []))):
            policy = yaml_content["Policies"][i]
            if policy.get("PolicyName") != policy_name:
                continue
            if policy.get("IncludeAccounts") or policy.get("ExcludeAccounts"):
                raise ValueError(
                    f"The {policy_name} policy has IncludeAccounts or ExcludeAccounts set"
                )
            successfully_merged_statement = True

            policy["Statement"].extend(
                CommentedSeq(change.policy.policy_document["Statement"])
            )
            yaml_content["Policies"][i][
                "Statement"
            ] = await minimize_iam_policy_statements(
                json.loads(json.dumps(policy["Statement"]))
            )
        if not successfully_merged_statement:
            # TODO: Need to add a new statement here, yay.
            yaml_content["Policies"].append(
                {
                    "PolicyName": policy_name,
                    "Statement": change.policy.policy_document["Statement"],
                }
            )
        with open(
            f"{repo.working_dir}/{change.principal.resource_identifier}", "w"
        ) as f:
            yaml.dump(yaml_content, f)
        # New
        buf = io.BytesIO()
        yaml.dump(yaml_content, buf)
        updated_text = buf.getvalue()

        request_changes.changes.append(
            GenericFileChangeModel(
                principal=primary_principal,
                action="attach",
                change_type="generic_file",
                policy=updated_text,
                old_policy=original_text,
                encoding="yaml",
            )
        )

    # TODO: Need to clean up directory
    return ExtendedRequestModel(
        principal=primary_principal,
        timestamp=int(time.time()),
        requester_email=user,
        approvers=[],
        request_status=RequestStatus.pending,
        changes=request_changes,
        requester_info=UserModel(
            email=user,
            extended_info=await auth.get_user_info(user),
            details_url=config.config_plugin().get_employee_info_url(user),
            photo_url=config.config_plugin().get_employee_photo_url(user),
        ),
        comments=[],
        cross_account=False,
    )

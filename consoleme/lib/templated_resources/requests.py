import io
import json
import time

from ruamel.yaml.comments import CommentedSeq

from consoleme.config import config
from consoleme.lib.aws import minimize_iam_policy_statements
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.scm.git import Repository
from consoleme.lib.scm.git.bitbucket import BitBucket
from consoleme.lib.yaml import yaml
from consoleme.models import (
    ChangeModelArray,
    ExtendedRequestModel,
    GenericFileChangeModel,
    PolicyModel,
    RequestCreationModel,
    RequestStatus,
    UserModel,
)

auth = get_plugin_by_name(config.get("plugins.auth", "default_auth"))()
log = config.get_logger()


async def generate_honeybee_request_from_change_model_array(
    request_creation: RequestCreationModel, user: str, extended_request_uuid: str
) -> ExtendedRequestModel:
    repositories_for_request = {}
    primary_principal = None
    t = int(time.time())
    generated_branch_name = f"{user}-{t}"
    policy_name = config.get(
        "generate_honeybee_request_from_change_model_array.policy_name",
        "self_service_generated",
    )
    repo_config = None

    # Checkout Git Repo and generate a branch name for the user's change
    for change in request_creation.changes.changes:
        if primary_principal and change.principal != primary_principal:
            raise Exception("Changes must all affect the same principal")
        primary_principal = change.principal
        discovered_repository_for_change = False
        if repositories_for_request.get(change.principal.repository_name):
            continue
        # Find repo
        for r in config.get("cache_resource_templates.repositories", []):
            if r["name"] == change.principal.repository_name:
                repo_config = r
                repo = Repository(
                    r["repo_url"], r["name"], r["authentication_settings"]["email"]
                )
                await repo.clone(depth=1)
                git_client = repo.git
                git_client.reset()
                git_client.checkout(b=generated_branch_name)
                repositories_for_request[change.principal.repository_name] = {
                    "main_branch_name": r["main_branch_name"],
                    "repo": repo,
                    "git_client": git_client,
                    "config": r,
                }
                discovered_repository_for_change = True
                break
        if not discovered_repository_for_change:
            raise Exception(
                "No matching repository found for change in ConsoleMe's configuration"
            )
    request_changes = ChangeModelArray(changes=[])
    affected_templates = []
    for change in request_creation.changes.changes:
        git_client = repositories_for_request[change.principal.repository_name][
            "git_client"
        ]
        repo = repositories_for_request[change.principal.repository_name]["repo"].repo
        main_branch_name = repositories_for_request[change.principal.repository_name][
            "main_branch_name"
        ]
        git_client.checkout(
            f"origin/{main_branch_name}", change.principal.resource_identifier
        )
        change_file_path = f"{repo.working_dir}/{change.principal.resource_identifier}"
        with open(change_file_path, "r") as f:
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

        # The PolicyModel is a representation of a single (usually inline) policy that a user has requested be merged
        # into a given template. If the policy is provided as a string, it's the contents of the full file (which
        # should include the user's requested change)
        if isinstance(change.policy, PolicyModel):
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
                yaml_content["Policies"].append(
                    {
                        "PolicyName": policy_name,
                        "Statement": change.policy.policy_document["Statement"],
                    }
                )
            with open(change_file_path, "w") as f:
                yaml.dump(yaml_content, f)
            # New
            buf = io.BytesIO()
            yaml.dump(yaml_content, buf)
            updated_text = buf.getvalue()

        elif isinstance(change.policy, str):
            # If the change is provided as a string, it represents the full change
            updated_text = change.policy
            with open(change_file_path, "w") as f:
                f.write(updated_text)
        else:
            raise Exception(
                "Unable to parse change from Honeybee templated role change request"
            )

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
        git_client.add(change.principal.resource_identifier)
        affected_templates.append(change.principal.resource_identifier)

    pull_request_url = ""
    if not request_creation.dry_run:
        commit_title = f"ConsoleMe Generated PR for {', '.join(affected_templates)}"
        commit_message = (
            f"This request was made through ConsoleMe Self Service\n\nUser: {user}\n\n"
            f"Justification: {request_creation.justification}"
        )

        git_client.commit(m=commit_message)
        git_client.push(u=["origin", generated_branch_name])
        if repo_config["code_repository_provider"] == "bitbucket":
            bitbucket = BitBucket(
                repo_config["code_repository_config"]["url"],
                config.get(
                    repo_config["code_repository_config"]["username_config_key"]
                ),
                config.get(
                    repo_config["code_repository_config"]["password_config_key"]
                ),
            )
            pull_request_url = await bitbucket.create_pull_request(
                repo_config["project_key"],
                repo_config["name"],
                repo_config["project_key"],
                repo_config["name"],
                generated_branch_name,
                repo_config["main_branch_name"],
                commit_title,
                commit_message,
            )
        else:
            raise Exception(
                f"Unsupported `code_repository_provider` specified in configuration: {repo_config}"
            )

    for repo_name, repo_details in repositories_for_request.items():
        await repo_details["repo"].cleanup()

    if not pull_request_url and not request_creation.dry_run:
        raise Exception("Unable to generate pull request URL")

    return ExtendedRequestModel(
        id=extended_request_uuid,
        request_url=pull_request_url,
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

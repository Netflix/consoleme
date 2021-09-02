import ujson as json

from consoleme.config import config
from consoleme.lib.account_indexers import get_account_id_to_name_mapping
from consoleme.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from consoleme.lib.self_service.models import (
    SelfServiceTypeaheadModel,
    SelfServiceTypeaheadModelArray,
)
from consoleme.models import (
    AwsResourcePrincipalModel,
    HoneybeeAwsResourceTemplatePrincipalModel,
)


async def cache_self_service_typeahead() -> SelfServiceTypeaheadModelArray:
    from consoleme.lib.templated_resources import retrieve_cached_resource_templates

    app_name_tag = config.get("cache_self_service_typeahead.app_name_tag")
    # Cache role and app information
    role_data = await retrieve_json_data_from_redis_or_s3(
        redis_key=config.get("aws.iamroles_redis_key", "IAM_ROLE_CACHE"),
        redis_data_type="hash",
        s3_bucket=config.get(
            "cache_iam_resources_across_accounts.all_roles_combined.s3.bucket"
        ),
        s3_key=config.get(
            "cache_iam_resources_across_accounts.all_roles_combined.s3.file",
            "account_resource_cache/cache_all_roles_v1.json.gz",
        ),
    )

    accounts_d = await get_account_id_to_name_mapping()

    typeahead_entries = []

    # We want templates to appear in Self-Service ahead of IAM roles, so we will cache them in that order.

    if config.get("cache_self_service_typeahead.cache_resource_templates"):
        resource_templates = await retrieve_cached_resource_templates(
            resource_type="iam_role", template_language="honeybee"
        )

        if resource_templates:
            for resource_template in resource_templates.templated_resources:
                typeahead_entries.append(
                    SelfServiceTypeaheadModel(
                        icon="users",
                        number_of_affected_resources=resource_template.number_of_accounts,
                        display_text=resource_template.name,
                        details_endpoint=f"/api/v2/templated_resource/{resource_template.repository_name}/"
                        + f"{resource_template.resource}",
                        principal=HoneybeeAwsResourceTemplatePrincipalModel(
                            principal_type="HoneybeeAwsResourceTemplate",
                            repository_name=resource_template.repository_name,
                            resource_identifier=resource_template.resource,
                            resource_url=resource_template.web_path,
                        ),
                    )
                )

    for role, details_j in role_data.items():
        account_id = role.split(":")[4]
        account_name = accounts_d.get(account_id, account_id)
        details = json.loads(details_j)
        policy = json.loads(details["policy"])
        role_name = policy.get("RoleName", policy["Arn"].split("/")[-1])
        app_name = None
        app_url = None
        if app_name_tag:
            for tag in policy.get("Tags", []):
                if tag["Key"] != app_name_tag:
                    continue
                app_name = tag["Value"]
                app_url = config.get("cache_self_service_typeahead.app_url", "").format(
                    app_name=app_name
                )
        typeahead_entries.append(
            SelfServiceTypeaheadModel(
                icon="user",
                number_of_affected_resources=1,
                display_text=role_name,
                account=account_name,
                application_name=app_name,
                application_url=app_url,
                principal=AwsResourcePrincipalModel(
                    principal_type="AwsResource", principal_arn=policy["Arn"]
                ),
                details_endpoint=f"/api/v2/roles/{account_id}/{role_name}",
            )
        )

    user_data = await retrieve_json_data_from_redis_or_s3(
        redis_key=config.get("aws.iamroles_redis_key", "IAM_USER_CACHE"),
        redis_data_type="hash",
        s3_bucket=config.get(
            "cache_iam_resources_across_accounts.all_users_combined.s3.bucket"
        ),
        s3_key=config.get(
            "cache_iam_resources_across_accounts.all_users_combined.s3.file",
            "account_resource_cache/cache_all_users_v1.json.gz",
        ),
        default={},
    )

    for user, details_j in user_data.items():
        account_id = user.split(":")[4]
        account_name = accounts_d.get(account_id, account_id)
        details = json.loads(details_j)
        policy = json.loads(details["policy"])
        user_name = policy.get("UserName", policy["Arn"].split("/")[-1])
        app_name = None
        app_url = None
        if app_name_tag:
            for tag in policy.get("Tags", []):
                if tag["Key"] != app_name_tag:
                    continue
                app_name = tag["Value"]
                app_url = config.get("cache_self_service_typeahead.app_url", "").format(
                    app_name=app_name
                )
        typeahead_entries.append(
            SelfServiceTypeaheadModel(
                icon="user",
                number_of_affected_resources=1,
                display_text=user_name,
                account=account_name,
                application_name=app_name,
                application_url=app_url,
                principal=AwsResourcePrincipalModel(
                    principal_type="AwsResource", principal_arn=policy["Arn"]
                ),
                details_endpoint=f"/api/v2/users/{account_id}/{user_name}",
            )
        )

    typeahead_data = SelfServiceTypeaheadModelArray(typeahead_entries=typeahead_entries)
    await store_json_results_in_redis_and_s3(
        json.loads(typeahead_data.json()),
        redis_key=config.get(
            "cache_self_service_typeahead.redis.key", "cache_self_service_typeahead_v1"
        ),
        s3_bucket=config.get("cache_self_service_typeahead.s3.bucket"),
        s3_key=config.get(
            "cache_self_service_typeahead.s3.file",
            "cache_self_service_typeahead/cache_self_service_typeahead_v1.json.gz",
        ),
    )
    return typeahead_data

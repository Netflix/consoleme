import re
from typing import Dict, List, Optional

import ujson as json
from policyuniverse.expander_minimizer import _expand_wildcard_action

from consoleme.config import config
from consoleme.exceptions.exceptions import InvalidRequestParameter, MustBeFte
from consoleme.handlers.base import BaseAPIV1Handler, BaseHandler, BaseMtlsHandler
from consoleme.lib.account_indexers import get_account_id_to_name_mapping
from consoleme.lib.cache import retrieve_json_data_from_redis_or_s3
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.redis import redis_get, redis_hgetall

log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
aws = get_plugin_by_name(config.get("plugins.aws", "default_aws"))()
auth = get_plugin_by_name(config.get("plugins.auth", "default_auth"))()


class AutocompleteHandler(BaseAPIV1Handler):
    async def get(self):
        """
        /api/v1/policyuniverse/autocomplete/?prefix=
        ---
        get:
            description: Supplies autocompleted permissions for the ace code editor.
            responses:
                200:
                    description: Returns a list of the matching permissions.
        """

        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")

        only_filter_services = False

        if (
            self.request.arguments.get("only_filter_services")
            and self.request.arguments.get("only_filter_services")[0].decode("utf-8")
            == "true"
        ):
            only_filter_services = True

        prefix = self.request.arguments.get("prefix")[0].decode("utf-8") + "*"
        results = _expand_wildcard_action(prefix)
        if only_filter_services:
            # We return known matching services in a format that the frontend expects to see them. We omit the wildcard
            # character returned by policyuniverse.
            services = sorted(list({r.split(":")[0].replace("*", "") for r in results}))
            results = [{"title": service} for service in services]
        else:
            results = [dict(permission=r) for r in results]
        self.write(json.dumps(results))
        await self.finish()


async def filter_resources(filter, resources, max=20):
    if filter:
        regexp = re.compile(r"{}".format(filter.strip()), re.IGNORECASE)
        results: List[str] = []
        for resource in resources:
            try:
                if regexp.search(str(resource.get(filter))):
                    if len(results) == max:
                        return results
                    results.append(resource)
            except re.error:
                # Regex error. Return no results
                pass
        return results
    else:
        return resources


async def handle_resource_type_ahead_request(cls):
    try:
        search_string: str = cls.request.arguments.get("search")[0].decode("utf-8")
    except TypeError:
        cls.send_error(400, message="`search` parameter must be defined")
        return

    try:
        resource_type: str = cls.request.arguments.get("resource")[0].decode("utf-8")
    except TypeError:
        cls.send_error(400, message="`resource_type` parameter must be defined")
        return

    account_id = None
    topic_is_hash = True
    account_id_optional: Optional[List[bytes]] = cls.request.arguments.get("account_id")
    if account_id_optional:
        account_id = account_id_optional[0].decode("utf-8")

    limit: int = 10
    limit_optional: Optional[List[bytes]] = cls.request.arguments.get("limit")
    if limit_optional:
        limit = int(limit_optional[0].decode("utf-8"))

    # By default, we only return the S3 bucket name of a resource and not the full ARN
    # unless you specifically request it
    show_full_arn_for_s3_buckets: Optional[bool] = cls.request.arguments.get(
        "show_full_arn_for_s3_buckets"
    )

    role_name = False
    if resource_type == "s3":
        topic = config.get("redis.s3_bucket_key", "S3_BUCKETS")
        s3_bucket = config.get("account_resource_cache.s3_combined.bucket")
        s3_key = config.get(
            "account_resource_cache.s3_combined.file",
            "account_resource_cache/cache_s3_combined_v1.json.gz",
        )
    elif resource_type == "sqs":
        topic = config.get("redis.sqs_queues_key", "SQS_QUEUES")
        s3_bucket = config.get("account_resource_cache.sqs_combined.bucket")
        s3_key = config.get(
            "account_resource_cache.sqs_combined.file",
            "account_resource_cache/cache_sqs_queues_combined_v1.json.gz",
        )
    elif resource_type == "sns":
        topic = config.get("redis.sns_topics_key ", "SNS_TOPICS")
        s3_bucket = config.get("account_resource_cache.sns_topics_combined.bucket")
        s3_key = config.get(
            "account_resource_cache.sns_topics_topics_combined.file",
            "account_resource_cache/cache_sns_topics_combined_v1.json.gz",
        )
    elif resource_type == "iam_arn":
        topic = config.get("aws.iamroles_redis_key ", "IAM_ROLE_CACHE")
        s3_bucket = config.get(
            "cache_iam_resources_across_accounts.all_roles_combined.s3.bucket"
        )
        s3_key = config.get(
            "cache_iam_resources_across_accounts.all_roles_combined.s3.file",
            "account_resource_cache/cache_all_roles_v1.json.gz",
        )
    elif resource_type == "iam_role":
        topic = config.get("aws.iamroles_redis_key ", "IAM_ROLE_CACHE")
        s3_bucket = config.get(
            "cache_iam_resources_across_accounts.all_roles_combined.s3.bucket"
        )
        s3_key = config.get(
            "cache_iam_resources_across_accounts.all_roles_combined.s3.file",
            "account_resource_cache/cache_all_roles_v1.json.gz",
        )
        role_name = True
    elif resource_type == "account":
        topic = None
        s3_bucket = None
        s3_key = None
        topic_is_hash = False
    elif resource_type == "app":
        topic = config.get("celery.apps_to_roles.redis_key", "APPS_TO_ROLES")
        s3_bucket = None
        s3_key = None
        topic_is_hash = False
    else:
        cls.send_error(404, message=f"Invalid resource_type: {resource_type}")
        return

    if not topic and resource_type != "account":
        raise InvalidRequestParameter("Invalid resource_type specified")

    if topic and topic_is_hash and s3_key:
        data = await retrieve_json_data_from_redis_or_s3(
            redis_key=topic, redis_data_type="hash", s3_bucket=s3_bucket, s3_key=s3_key
        )
    elif topic:
        data = await redis_get(topic)

    results: List[Dict] = []

    unique_roles: List[str] = []

    if resource_type == "account":
        account_and_id_list = []
        account_ids_to_names = await get_account_id_to_name_mapping()
        for account_id, account_name in account_ids_to_names.items():
            account_and_id_list.append(f"{account_name} ({account_id})")
        for account in account_and_id_list:
            if search_string.lower() in account.lower():
                results.append({"title": account})
    elif resource_type == "app":
        results = {}
        all_role_arns = []
        all_role_arns_j = await redis_hgetall(
            (config.get("aws.iamroles_redis_key", "IAM_ROLE_CACHE"))
        )
        if all_role_arns_j:
            all_role_arns = all_role_arns_j.keys()
        # ConsoleMe (Account: Test, Arn: arn)
        # TODO: Make this OSS compatible and configurable
        try:
            accounts = await get_account_id_to_name_mapping()
        except Exception as e:  # noqa
            accounts = {}

        app_to_role_map = {}
        if data:
            app_to_role_map = json.loads(data)
        seen: Dict = {}
        seen_roles = {}
        for app_name, roles in app_to_role_map.items():
            if len(results.keys()) > 9:
                break
            if search_string.lower() in app_name.lower():
                results[app_name] = {"name": app_name, "results": []}
                for role in roles:
                    account_id = role.split(":")[4]
                    account = accounts.get(account_id, "")
                    parsed_app_name = (
                        f"{app_name} on {account} ({account_id}) ({role})]"
                    )
                    if seen.get(parsed_app_name):
                        continue
                    seen[parsed_app_name] = True
                    seen_roles[role] = True
                    results[app_name]["results"].append(
                        {"title": role, "description": account}
                    )
        for role in all_role_arns:
            if len(results.keys()) > 9:
                break
            if search_string.lower() in role.lower():
                if seen_roles.get(role):
                    continue
                account_id = role.split(":")[4]
                account = accounts.get(account_id, "")
                if not results.get("Unknown App"):
                    results["Unknown App"] = {"name": "Unknown App", "results": []}
                results["Unknown App"]["results"].append(
                    {"title": role, "description": account}
                )

    else:
        if not data:
            return []
        for k, v in data.items():
            if account_id and k != account_id:
                continue
            if role_name:
                try:
                    r = k.split("role/")[1]
                except IndexError:
                    continue
                if search_string.lower() in r.lower():
                    if r not in unique_roles:
                        unique_roles.append(r)
                        results.append({"title": r})
            elif resource_type == "iam_arn":
                if k.startswith("arn:") and search_string.lower() in k.lower():
                    results.append({"title": k})
            else:
                list_of_items = json.loads(v)
                for item in list_of_items:
                    # A Hack to get S3 to show full ARN, and maintain backwards compatibility
                    # TODO: Fix this in V2 of resource specific typeahead endpoints
                    if resource_type == "s3" and show_full_arn_for_s3_buckets:
                        item = f"arn:aws:s3:::{item}"
                    if search_string.lower() in item.lower():
                        results.append({"title": item, "account_id": k})
                    if len(results) > limit:
                        break
            if len(results) > limit:
                break
    return results


class ApiResourceTypeAheadHandler(BaseMtlsHandler):
    async def get(self):
        requester_type = self.requester.get("type", "")
        if requester_type == "application":
            if self.requester["name"] not in config.get("api_auth.valid_entities", []):
                raise Exception("Call does not originate from a valid API caller")
        elif requester_type == "user":
            # TODO: do we need to block contractor access?
            pass
        else:
            raise Exception("Call does not originate from a valid API caller")

        results = await handle_resource_type_ahead_request(self)
        self.write(json.dumps(results))


class ResourceTypeAheadHandler(BaseHandler):
    async def get(self):
        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")
        results = await handle_resource_type_ahead_request(self)
        self.write(json.dumps(results))

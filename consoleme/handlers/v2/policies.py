import ujson as json

from consoleme.config import config
from consoleme.exceptions.exceptions import MustBeFte
from consoleme.handlers.base import BaseAPIV2Handler, BaseHandler
from consoleme.lib.aws import get_all_iam_managed_policies_for_account
from consoleme.lib.cache import retrieve_json_data_from_redis_or_s3
from consoleme.lib.generic import filter_table
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.policies import get_url_for_resource
from consoleme.lib.timeout import Timeout

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()


class PoliciesPageConfigHandler(BaseHandler):
    async def get(self):
        """
        /api/v2/policies_page_config
        ---
        get:
            description: Retrieve Policies Page Configuration
            responses:
                200:
                    description: Returns Policies Page Configuration
        """
        default_configuration = {
            "pageName": "Policies",
            "pageDescription": "View all of the AWS Resources we know about.",
            "tableConfig": {
                "expandableRows": True,
                "dataEndpoint": "/api/v2/policies?markdown=true",
                "sortable": False,
                "totalRows": 1000,
                "rowsPerPage": 50,
                "serverSideFiltering": True,
                "columns": [
                    {
                        "placeholder": "Account ID",
                        "key": "account_id",
                        "type": "input",
                        "style": {"width": "110px"},
                    },
                    {
                        "placeholder": "Account",
                        "key": "account_name",
                        "type": "input",
                        "style": {"width": "90px"},
                    },
                    {
                        "placeholder": "Resource",
                        "key": "arn",
                        "type": "link",
                        "width": 6,
                        "style": {"whiteSpace": "normal", "wordBreak": "break-all"},
                    },
                    {
                        "placeholder": "Tech",
                        "key": "technology",
                        "type": "input",
                        "style": {"width": "70px"},
                    },
                    {
                        "placeholder": "Template",
                        "key": "templated",
                        "type": "input",
                        "style": {"width": "100px"},
                    },
                    {
                        "placeholder": "Errors",
                        "key": "errors",
                        "color": "red",
                        "width": 1,
                    },
                ],
            },
        }

        table_configuration = config.get(
            "PoliciesTableConfigHandler.configuration", default_configuration
        )

        self.write(table_configuration)


class PoliciesHandler(BaseAPIV2Handler):
    """Handler for /api/v2/policies

    Api endpoint to list and filter policy requests.
    """

    allowed_methods = ["POST"]

    async def post(self):
        """
        POST /api/v2/policies
        """
        arguments = {k: self.get_argument(k) for k in self.request.arguments}
        markdown = arguments.get("markdown")

        arguments = json.loads(self.request.body)
        filters = arguments.get("filters")
        limit = arguments.get("limit", 1000)
        tags = {"user": self.user}
        stats.count("PoliciesHandler.post", tags=tags)
        log_data = {
            "function": "PoliciesHandler.post",
            "user": self.user,
            "message": "Writing policies",
            "limit": limit,
            "filters": filters,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        policies = await retrieve_json_data_from_redis_or_s3(
            redis_key=config.get("policies.redis_policies_key", "ALL_POLICIES"),
            s3_bucket=config.get("cache_policies_table_details.s3.bucket"),
            s3_key=config.get("cache_policies_table_details.s3.file"),
            default=[],
        )

        if filters:
            try:
                with Timeout(seconds=5):
                    for filter_key, filter_value in filters.items():
                        policies = await filter_table(
                            filter_key, filter_value, policies
                        )
            except TimeoutError:
                self.write("Query took too long to run. Check your filter.")
                await self.finish()
                raise

        if markdown:
            policies_to_write = []
            for policy in policies[0:limit]:
                resource_name = policy.get("arn").split(":")[5]
                if "/" in resource_name:
                    resource_name = resource_name.split("/")[-1]
                region = policy["arn"].split(":")[3]
                url = await get_url_for_resource(
                    policy["arn"],
                    policy["technology"],
                    policy["account_id"],
                    region,
                    resource_name,
                )
                if url:
                    policy["arn"] = f"[{policy['arn']}]({url})"
                if not policy.get("templated"):
                    policy["templated"] = "N/A"
                else:
                    if "/" in policy["templated"]:
                        link_name = policy["templated"].split("/")[-1]
                        policy["templated"] = f"[{link_name}]({policy['templated']})"
                policies_to_write.append(policy)
        else:
            policies_to_write = policies[0:limit]
        self.write(json.dumps(policies_to_write))
        return


class ManagedPoliciesHandler(BaseHandler):
    async def get(self, account_id):
        """
        Retrieve a list of managed policies for an account.
        """
        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")
        all_account_managed_policies = await get_all_iam_managed_policies_for_account(
            account_id
        )
        self.write(json.dumps(all_account_managed_policies))

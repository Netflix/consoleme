import sys

import ujson as json

from consoleme.config import config
from consoleme.handlers.base import BaseAPIV2Handler, BaseHandler
from consoleme.lib.cache import retrieve_json_data_from_redis_or_s3
from consoleme.lib.generic import filter_table
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.policies import get_url_for_resource
from consoleme.lib.timeout import Timeout

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()


class PolicyReviewV2Handler(BaseHandler):
    """
        Handler for /policies/request_v2/{request_id}

        GET - Get requests v2 page # TODO: add better description

    """

    allowed_methods = ["GET"]

    async def get(self, request_id):

        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "ip": self.ip,
            "policy_request_id": request_id,
        }
        log.debug(log_data)
        stats.count(f"{log_data['function']}", tags={"user": self.user})

        await self.render(
            "policy_review_v2.html",
            page_title="ConsoleMe - Policy Review",
            current_page="policies",
            user=self.user,
            user_groups=self.groups,
            config=config,
        )


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


class PoliciesTableConfigHandler(BaseHandler):
    async def get(self):
        """
        /api/v2/policies_table_config
        ---
        get:
            description: Retrieve Policies Table Configuration
            responses:
                200:
                    description: Returns Policies Table Configuration
        """
        default_configuration = {
            "expandableRows": True,
            "tableName": "Policies",
            "tableDescription": "View all of the AWS Resources we know about.",
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
                    "type": "input",
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
                {"placeholder": "Errors", "key": "errors", "color": "red", "width": 1},
            ],
        }

        table_configuration = config.get(
            "PoliciesTableConfigHandler.configuration", default_configuration
        )

        self.write(table_configuration)

import ujson as json

from consoleme.config import config
from consoleme.handlers.base import BaseAPIV2Handler, BaseHandler
from consoleme.lib.cache import retrieve_json_data_from_redis_or_s3
from consoleme.lib.generic import filter_table
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.timeout import Timeout

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()


class RequestsHandler(BaseAPIV2Handler):
    """Handler for /api/v2/requests_table

    Api endpoint to list and filter policy requests.
    """

    allowed_methods = ["POST"]

    async def post(self):
        """
        POST /api/v2/requests
        """
        cache_key = config.get(
            "cache_all_policy_requests.redis_key", "ALL_POLICY_REQUESTS"
        )
        s3_bucket = config.get("cache_policy_requests.s3.bucket")
        s3_key = config.get("cache_policy_requests.s3.file")
        arguments = json.loads(self.request.body)
        filters = arguments.get("filters")
        limit = arguments.get("limit", 1000)
        tags = {"user": self.user}
        stats.count("RequestsHandler.post", tags=tags)
        log_data = {
            "function": "RequestsHandler.post",
            "user": self.user,
            "message": "Writing all available requests",
            "limit": limit,
            "filters": filters,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        requests = await retrieve_json_data_from_redis_or_s3(
            cache_key, s3_bucket=s3_bucket, s3_key=s3_key
        )
        if filters:
            try:
                with Timeout(seconds=5):
                    for filter_key, filter_value in filters.items():
                        requests = await filter_table(
                            filter_key, filter_value, requests
                        )
            except TimeoutError:
                self.write("Query took too long to run. Check your filter.")
                await self.finish()
                raise

        self.write(json.dumps(requests[0:limit]))
        return


class RequestDetailHandler(BaseAPIV2Handler):
    """Handler for /api/v2/requests/{request_id}

    Allows read and update access to a specific request.
    """

    allowed_methods = ["GET", "PUT"]

    async def get(self, request_id):
        """
        GET /api/v2/requests/{request_id}
        """
        tags = {"user": self.user}
        stats.count("RequestDetailHandler.get", tags=tags)
        log_data = {
            "function": "RequestDetailHandler.get",
            "user": self.user,
            "message": "Writing request details",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Get request details")

    async def put(self, request_id):
        """
        PUT /api/v2/requests/{request_id}
        """
        tags = {"user": self.user}
        stats.count("RequestDetailHandler.put", tags=tags)
        log_data = {
            "function": "RequestDetailHandler.put",
            "user": self.user,
            "message": "Updating request details",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Update request details")


class RequestsTableConfigHandler(BaseHandler):
    async def get(self):
        """
        /requests_table_config
        ---
        get:
            description: Retrieve Requests Table Configuration
            responses:
                200:
                    description: Returns Requests Table Configuration
        """
        default_configuration = {
            "expandableRows": True,
            "expandOnRowClicked": False,
            "pagination": True,
            "highlightOnHover": True,
            "striped": True,
            "subHeader": True,
            "filterColumns": True,
            "tableName": "Requests",
            "dataEndpoint": "/api/v2/requests",
            "grow": 3,
            "totalRows": 1000,
            "wrap": True,
            "keyField": "request_id",
            "className": "ConsoleMeDataTable",
            "serverSideFiltering": True,
            "desiredColumns": [
                {"name": "Username", "selector": "username"},
                {"name": "Arn", "selector": "arn"},
                {"name": "Request Time", "selector": "request_time"},
                {"name": "Status", "selector": "status"},
                {
                    "name": "Request ID",
                    "selector": "request_id",
                    "cell": {
                        "type": "href",
                        "href": "/policies/request/{row.request_id}",
                        "name": "{row.request_id}",
                    },
                },
                {"name": "Policy Name", "selector": "policy_name"},
                {"name": "Last Updated By", "selector": "updated_by"},
            ],
        }

        table_configuration = config.get(
            "RequestsTableConfigHandler.configuration", default_configuration
        )

        self.write(table_configuration)


class RequestsWebHandler(BaseHandler):
    async def get(self):
        """
        /requests
        ---
        get:
            description: Entry point to Requests view
            responses:
                200:
                    description: Returns Requests view
        """

        await self.render(
            "requests.html",
            page_title="ConsoleMe - Requests",
            current_page="requests",  # TODO add a page header for me
            user=self.user,
            user_groups=self.groups,
            config=config,
        )

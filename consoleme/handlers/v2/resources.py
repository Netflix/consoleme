import sys
from datetime import datetime, timedelta

import ujson as json

from consoleme.config import config
from consoleme.exceptions.exceptions import MustBeFte
from consoleme.handlers.base import BaseHandler
from consoleme.lib.account_indexers import get_account_id_to_name_mapping
from consoleme.lib.aws import fetch_resource_details
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.policies import can_manage_policy_requests

log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics"))()
aws = get_plugin_by_name(config.get("plugins.aws"))()
group_mapping = get_plugin_by_name(config.get("plugins.group_mapping"))()
auth = get_plugin_by_name(config.get("plugins.auth"))()
internal_policies = get_plugin_by_name(config.get("plugins.internal_policies"))()


class ResourceDetailHandler(BaseHandler):
    async def get(self, account_id, resource_type, region=None, resource_name=None):
        if not self.user:
            return
        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")
        read_only = False

        can_save_delete = await can_manage_policy_requests(self.user, self.groups)

        account_id_for_arn: str = account_id
        if resource_type == "s3":
            account_id_for_arn = ""
        arn = f"arn:aws:{resource_type}:{region or ''}:{account_id_for_arn}:{resource_name}"

        stats.count(
            "ResourcePolicyEditHandler.get", tags={"user": self.user, "arn": arn}
        )

        log_data = {
            "user": self.user,
            "ip": self.ip,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "arn": arn,
        }

        log.debug(log_data)

        resource_details = await fetch_resource_details(
            account_id, resource_type, resource_name, region
        )

        # TODO: Get S3 errors for s3 buckets only, else CT errors
        yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y%m%d")
        s3_query_url = None
        if resource_type == "s3":
            s3_query_url = config.get("s3.bucket_query_url")
        all_s3_errors = None
        if s3_query_url:
            s3_query_url = s3_query_url.format(
                yesterday=yesterday, bucket_name=f"'{resource_name}'"
            )
            s3_error_topic = config.get("redis.s3_errors", "S3_ERRORS")
            all_s3_errors = self.red.get(s3_error_topic)

        s3_errors = []
        if all_s3_errors:
            s3_errors = json.loads(all_s3_errors).get(arn, [])

        account_ids_to_name = await get_account_id_to_name_mapping()
        # TODO(ccastrapel/psanders): Make a Swagger spec for this
        self.write(
            dict(
                arn=arn,
                resource_details=resource_details,
                account_id=account_id,
                account_name=account_ids_to_name.get(account_id, None),
                read_only=read_only,
                can_save_delete=can_save_delete,
                s3_errors=s3_errors,
                s3_query_url=s3_query_url,
            )
        )

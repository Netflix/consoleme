from consoleme.config import config
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.lib.policies import can_manage_policy_requests


class SelfServiceConfigHandler(BaseAPIV2Handler):
    allowed_methods = ["GET"]

    async def get(self):
        self_service_iam_config: dict = config.get("self_service_iam")
        self_service_iam_config[
            "admin_bypass_approval_enabled"
        ] = await can_manage_policy_requests(self.groups)
        self.write(self_service_iam_config)

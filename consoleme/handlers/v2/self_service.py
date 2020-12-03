from consoleme.config import config
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.lib.auth import can_admin_policies


class SelfServiceConfigHandler(BaseAPIV2Handler):
    allowed_methods = ["GET"]

    async def get(self):
        admin_bypass_approval_enabled: bool = can_admin_policies(self.user, self.groups)
        self_service_iam_config: dict = config.get("self_service_iam")

        self.write(
            {
                "admin_bypass_approval_enabled": admin_bypass_approval_enabled,
                **self_service_iam_config,
            }
        )

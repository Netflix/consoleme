from consoleme.config import config
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.lib.auth import can_admin_policies
from consoleme.lib.defaults import (
    PERMISSION_TEMPLATE_DEFAULTS,
    SELF_SERVICE_IAM_DEFAULTS,
)


class SelfServiceConfigHandler(BaseAPIV2Handler):
    allowed_methods = ["GET"]

    async def get(self):
        admin_bypass_approval_enabled: bool = can_admin_policies(self.user, self.groups)
        export_to_terraform_enabled: bool = config.get(
            "export_to_terraform_enabled", False
        )
        self_service_iam_config: dict = config.get(
            "self_service_iam", SELF_SERVICE_IAM_DEFAULTS
        )

        self.write(
            {
                "admin_bypass_approval_enabled": admin_bypass_approval_enabled,
                "export_to_terraform_enabled": export_to_terraform_enabled,
                **self_service_iam_config,
            }
        )


class PermissionTemplatesHandler(BaseAPIV2Handler):
    allowed_methods = ["GET"]

    async def get(self):
        permission_templates_dynamic_config_raw: dict = config.get(
            "dynamic_config.permission_templates"
        )

        permission_templates_dynamic_config: dict = [
            value for _, value in permission_templates_dynamic_config_raw.items()
        ]

        permission_templates_config: dict = config.get(
            "permission_templates", PERMISSION_TEMPLATE_DEFAULTS
        )
        temp = [*permission_templates_config, *permission_templates_dynamic_config]

        permission_templates = [
            dict(t) for t in {tuple(sorted(p.items())) for p in temp}
        ]

        self.write({"permission_templates": permission_templates})

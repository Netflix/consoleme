from typing import Any, Dict, List

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

        # Help message can be configured with Markdown for link handling
        help_message: str = config.get("self_service_iam_help_message")

        self.write(
            {
                "admin_bypass_approval_enabled": admin_bypass_approval_enabled,
                "export_to_terraform_enabled": export_to_terraform_enabled,
                "help_message": help_message,
                **self_service_iam_config,
            }
        )


class PermissionTemplatesHandler(BaseAPIV2Handler):
    allowed_methods = ["GET"]

    async def get(self):
        """
        Returns permission templates.

        Combines permission templates from dynamic configuration to the ones discovered in static configuration, with a
        priority to the templates defined in dynamic configuration.

        If no permission_templates are defined in static configuration, this function will substitute the static
        configuration templates with PERMISSION_TEMPLATE_DEFAULTS.
        """
        permission_templates_dynamic_config: List[Dict[str, Any]] = config.get(
            "dynamic_config.permission_templates", []
        )

        permission_templates_config: List[Dict[str, Any]] = config.get(
            "permission_templates", PERMISSION_TEMPLATE_DEFAULTS
        )

        seen = set()
        compiled_permission_templates = []
        for item in [
            *permission_templates_dynamic_config,
            *permission_templates_config,
        ]:
            if item["key"] in seen:
                continue
            compiled_permission_templates.append(item)
            seen.add(item["key"])

        self.write({"permission_templates": compiled_permission_templates})

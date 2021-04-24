from typing import Dict

from consoleme.config import config
from consoleme.handlers.base import BaseAPIV1Handler
from consoleme.lib.account_indexers import get_account_id_to_name_mapping
from consoleme.lib.auth import (
    can_admin_policies,
    can_create_roles,
    can_delete_roles,
    can_edit_dynamic_config,
)
from consoleme.lib.generic import get_random_security_logo, is_in_group
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.v2.user_profile import get_custom_page_header

stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
log = config.get_logger()


class UserProfileHandler(BaseAPIV1Handler):
    async def get(self):
        """
        Provide information about site configuration for the frontend
        :return:
        """
        is_contractor = config.config_plugin().is_contractor(self.user)
        site_config = {
            "consoleme_logo": await get_random_security_logo(),
            "google_tracking_uri": config.get("google_analytics.tracking_url"),
            "documentation_url": config.get(
                "documentation_page", "https://hawkins.gitbook.io/consoleme/"
            ),
            "support_contact": config.get("support_contact"),
            "support_chat_url": config.get(
                "support_chat_url", "https://discord.com/invite/nQVpNGGkYu"
            ),
            "security_logo": config.get("security_logo.image"),
            "security_url": config.get("security_logo.url"),
        }

        custom_page_header: Dict[str, str] = await get_custom_page_header(
            self.user, self.groups
        )
        user_profile = {
            "site_config": site_config,
            "user": self.user,
            "can_logout": config.get("auth.set_auth_cookie", False),
            "is_contractor": is_contractor,
            "employee_photo_url": config.config_plugin().get_employee_photo_url(
                self.user
            ),
            "employee_info_url": config.config_plugin().get_employee_info_url(
                self.user
            ),
            "authorization": {
                "can_edit_policies": can_admin_policies(self.user, self.groups),
                "can_create_roles": can_create_roles(self.user, self.groups),
                "can_delete_roles": can_delete_roles(self.user, self.groups),
            },
            "pages": {
                "header": {
                    "custom_header_message_title": custom_page_header.get(
                        "custom_header_message_title", ""
                    ),
                    "custom_header_message_text": custom_page_header.get(
                        "custom_header_message_text", ""
                    ),
                    "custom_header_message_route": custom_page_header.get(
                        "custom_header_message_route", ""
                    ),
                },
                "groups": {
                    "enabled": config.get("headers.group_access.enabled", False)
                },
                "users": {"enabled": config.get("headers.group_access.enabled", False)},
                "policies": {
                    "enabled": config.get("headers.policies.enabled", True)
                    and not is_contractor
                },
                "self_service": {
                    "enabled": config.get("enable_self_service", True)
                    and not is_contractor
                },
                "api_health": {
                    "enabled": is_in_group(
                        self.user,
                        self.groups,
                        config.get("groups.can_edit_health_alert", []),
                    )
                },
                "audit": {
                    "enabled": is_in_group(
                        self.user, self.groups, config.get("groups.can_audit", [])
                    )
                },
                "config": {"enabled": can_edit_dynamic_config(self.user, self.groups)},
            },
            "accounts": await get_account_id_to_name_mapping(),
        }

        self.set_header("Content-Type", "application/json")
        self.write(user_profile)

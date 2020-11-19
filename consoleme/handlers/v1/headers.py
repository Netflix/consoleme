from tornado.escape import xhtml_escape

from consoleme.config import config
from consoleme.handlers.base import BaseAPIV1Handler, BaseHandler, BaseMtlsHandler
from consoleme.lib.aws import can_delete_roles
from consoleme.lib.generic import get_random_security_logo, is_in_group
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.policies import can_manage_policy_requests

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()


class UserProfileHandler(BaseAPIV1Handler):
    async def get(self):
        """
        Provide information about the user profile for the frontend
        :return:
        """
        is_contractor = config.config_plugin().is_contractor(self.user)
        user_profile = {
            "user": self.user,
            "is_contractor": is_contractor,
            "employee_photo_url": config.config_plugin().get_employee_photo_url(
                self.user
            ),
            "employee_info_url": config.config_plugin().get_employee_info_url(
                self.user
            ),
            "authorization": {
                "can_edit_policies": await can_manage_policy_requests(
                    self.user, self.groups
                ),
                "can_create_roles": is_in_group(
                    self.user, self.groups, config.get("groups.can_create_roles", [])
                ),
                "can_delete_roles": await can_delete_roles(self.groups),
            },
            "pages": {
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
                "config": {
                    "enabled": is_in_group(
                        self.user, self.groups, config.get("groups.can_edit_config", [])
                    )
                },
            },
        }
        self.set_header("Content-Type", "application/json")
        self.write(user_profile)


class SiteConfigHandler(BaseAPIV1Handler):
    async def get(self):
        """
        Provide information about site configuration for the frontend
        :return:
        """
        site_config = {
            "consoleme_logo": await get_random_security_logo(),
            "google_tracking_uri": config.get("google_analytics.tracking_url"),
            "documentation_url": config.get("documentation_page"),
            "support_contact": config.get("support_contact"),
            "support_chat_url": config.get("support_chat_url"),
            "security_logo": config.get("security_logo.url"),
        }
        self.set_header("Content-Type", "application/json")
        self.write(site_config)


class HeaderHandler(BaseHandler):
    async def get(self):
        """
        Show request headers for API requests. AuthZ is required.
            ---
            description: Shows all headers received by server
            responses:
                200:
                    description: Pretty-formatted list of headers.
        """

        if not self.user:
            return
        log_data = {
            "user": self.user,
            "function": "myheaders.get",
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        stats.count("myheaders.get", tags={"user": self.user})

        response_html = []

        for k, v in dict(self.request.headers).items():
            if k.lower() in map(str.lower, config.get("headers.sensitive_headers", [])):
                continue
            response_html.append(
                f"<p><strong>{xhtml_escape(k)}</strong>: {xhtml_escape(v)}</p>"
            )

        self.write("{}".format("\n".join(response_html)))


class ApiHeaderHandler(BaseMtlsHandler):
    async def get(self):
        """
        Show request headers for API requests. No AuthZ required.
            ---
            description: Shows all headers received by server
            responses:
                200:
                    description: Pretty-formatted list of headers.
        """
        log_data = {
            "function": "apimyheaders.get",
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        stats.count("apimyheaders.get")
        response = {}
        for k, v in dict(self.request.headers).items():
            if k.lower() in map(str.lower, config.get("headers.sensitive_headers", [])):
                continue
            response[k] = v

        self.write(response)

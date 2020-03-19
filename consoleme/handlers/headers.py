from tornado.escape import xhtml_escape

from consoleme.config import config
from consoleme.handlers.base import BaseHandler, BaseMtlsHandler
from consoleme.lib.generic import is_in_group, get_random_security_logo
from consoleme.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()


class PageHeaderHandler(BaseHandler):
    async def get(self):
        """
        Provide information about the user and page headers for the frontend
        :return:
        """
        is_contractor = config.config_plugin().is_contractor(self.user)
        page_header_details = {
            "user": self.user,
            "is_contractor": is_contractor,
            "employee_photo_url": config.config_plugin().get_employee_photo_url(
                self.user
            ),
            "employee_info_url": config.config_plugin().get_employee_info_url(
                self.user
            ),
            "google_tracking_uri": config.get("google_analytics.tracking_url"),
            "documentation_url": config.get("documentation_page"),
            "support_contact": config.get("support_contact"),
            "support_slack": config.get("support_slack"),
            "security_logo": config.get("security_logo.url"),
            "consoleme_logo": await get_random_security_logo(),
            "pages": {
                "groups": {"enabled": config.get("headers.group_access.enabled", True)},
                "users": {"enabled": config.get("headers.group_access.enabled", True)},
                "policies": {
                    "enabled": config.get("headers.policies.enabled", True)
                    and not is_contractor
                },
                "self_service": {"enabled": config.get("enable_self_service")},
                "api_health": {
                    "enabled": is_in_group(
                        self.groups, config.get("groups.can_edit_health_alert", [])
                    )
                },
                "audit": {
                    "enabled": is_in_group(
                        self.groups, config.get("groups.can_audit", [])
                    )
                },
                "config": {
                    "enabled": is_in_group(
                        self.groups, config.get("groups.can_edit_config", [])
                    )
                },
            },
        }
        self.set_header("Content-Type", "application/json")
        self.write(page_header_details)


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

        self.write(dict(self.request.headers))

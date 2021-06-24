from tornado.escape import xhtml_escape

from consoleme.config import config
from consoleme.handlers.base import BaseHandler, BaseMtlsHandler
from consoleme.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
log = config.get_logger()


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

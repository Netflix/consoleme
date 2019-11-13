import datetime
import sys
import ujson as json

import dateutil
import pkg_resources
from asgiref.sync import sync_to_async
from tornado.template import Loader

from consoleme.config import config
from consoleme.exceptions.exceptions import UnauthorizedToAccess
from consoleme.handlers.base import BaseHandler
from consoleme.lib.generic import is_in_group, regex_filter
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.redis import redis_get
from consoleme.lib.timeout import Timeout

stats = get_plugin_by_name(config.get("plugins.metrics"))()
log = config.get_logger()
loader = Loader(pkg_resources.resource_filename("consoleme", "templates"))
aws = get_plugin_by_name(config.get("plugins.aws"))()
auth = get_plugin_by_name(config.get("plugins.auth"))()
group_mapping = get_plugin_by_name(config.get("plugins.group_mapping"))()


class AuditHandler(BaseHandler):
    async def get(self) -> None:
        """
        /audit/ - Administrative endpoint used to show audit logs
        ---
        get:
            description: Renders page that will make XHR request to get audit information
            responses:
                200:
                    description: Renders page that will make subsequent XHR requests
                403:
                    description: User has failed authn/authz.
        """

        if not self.user:
            return

        authorized = is_in_group(self.groups, config.get("groups.can_audit", []))

        if not authorized:
            raise UnauthorizedToAccess("You are not authorized to view this page.")

        stats.count("audithandler.get", tags={"user": self.user, "ip": self.ip})

        log_data = {
            "user": self.user,
            "ip": self.ip,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }

        log.debug(log_data)
        await self.render(
            "audit.html",
            page_title="ConsoleMe - Audit",
            current_page="audit",
            user=self.user,
            user_groups=self.groups,
            config=config,
        )


class GetAuditLogsHandler(BaseHandler):
    async def get(self) -> None:
        """
        /get_audit_logs/ - Filters and returns audit log information from DynamoDB.
        ---
        get:
            description: Returns audit log information
            responses:
                200:
                    description: returns JSON with filtered audit information.
                403:
                    description: User has failed authn/authz.
        """

        authorized = is_in_group(self.groups, config.get("groups.can_audit", []))

        if not authorized:
            raise UnauthorizedToAccess("You are not authorized to view this page.")

        draw = int(self.request.arguments.get("draw")[0])
        length = int(self.request.arguments.get("length")[0])
        start = int(self.request.arguments.get("start")[0])
        finish = start + length
        group_search = self.request.arguments.get("columns[0][search][value]")[
            0
        ].decode("utf-8")
        action_search = self.request.arguments.get("columns[1][search][value]")[
            0
        ].decode("utf-8")
        affected_user_search = self.request.arguments.get("columns[2][search][value]")[
            0
        ].decode("utf-8")
        acting_user_search = self.request.arguments.get("columns[3][search][value]")[
            0
        ].decode("utf-8")
        updated_at_from = self.request.arguments.get("datepicker_from")[0].decode(
            "utf-8"
        )
        updated_at_to = self.request.arguments.get("datepicker_to")[0].decode("utf-8")
        log_id_search = self.request.arguments.get("columns[5][search][value]")[
            0
        ].decode("utf-8")

        topic = config.get("redis.audit_log_key", "CM_AUDIT_LOGS")
        entries_j = await redis_get(topic)
        entries = json.loads(entries_j)

        for entry in entries:
            entry["updated_at"] = datetime.datetime.fromtimestamp(
                entry["updated_at"]
            ).strftime("%x %X")

        data = []
        filters = [
            {"field": "group", "filter": group_search},
            {"field": "action", "filter": action_search},
            {"field": "username", "filter": affected_user_search},
            {"field": "updated_by", "filter": acting_user_search},
            {
                "field": "updated_at",
                "filter": "date",
                "type": "date",
                "from_date": updated_at_from,
                "to_date": updated_at_to,
            },
            {"field": "uuid", "filter": log_id_search},
        ]

        results = sorted(
            entries, key=lambda e: dateutil.parser.parse(e["updated_at"]), reverse=True
        )

        try:
            with Timeout(seconds=5):
                for f in filters:
                    results = await sync_to_async(regex_filter)(f, results)
        except TimeoutError:
            self.write("Query took too long to run. Check your filter.")
            await self.finish()
            raise

        for entry in results[start:finish]:
            data.append(
                [
                    entry["group"],
                    entry.get("action"),
                    entry.get("username"),
                    entry.get("updated_by"),
                    entry.get("updated_at"),
                    entry.get("uuid"),
                ]
            )
            if len(data) == length:
                break

        response = {
            "draw": draw,
            "recordsTotal": len(entries),
            "recordsFiltered": len(results),
            "data": data,
        }
        self.write(response)
        await self.finish()

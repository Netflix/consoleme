import sys

from consoleme.config import config
from consoleme.handlers.base import BaseMtlsHandler
from consoleme.lib.cloud_credential_authorization_mapping import (
    CredentialAuthorizationMapping,
)
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.models import Status2, WebResponse

log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
credential_mapping = CredentialAuthorizationMapping()


def _get_last_page(total: int, page_size: int) -> int:
    pages = int(total / page_size)
    if not total % page_size:
        pages += 1
    return pages


class AuditRolesHandler(BaseMtlsHandler):
    """Handler for /api/v2/audit/roles

    Returns a list of all roles known to ConsoleMe
    """

    allowed_methods = ["GET"]

    def check_xsrf_cookie(self) -> None:
        pass

    async def get(self):
        """
        GET /api/v2/audit/roles
        """
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }

        page = self.get_argument("page", "0")
        try:
            page = int(page)
        except ValueError:
            log_data["message"] = f"invalid value for page: {page}"
            log.warning(log_data)
            page = 0

        count = self.get_argument("count", "1000")
        try:
            count = int(count)
        except ValueError:
            log_data["message"] = f"invalid value for count: {count}"
            log.warning(log_data)
            count = 1000

        if page < 0:
            page = 0
        if count <= 0:
            count = 1000

        app_name = self.requester.get("name") or self.requester.get("username")
        stats.count(
            "AuditRoleHandler.get",
            tags={
                "requester": app_name,
            },
        )

        roles = await credential_mapping.all_roles(
            paginate=True, page=page, count=count
        )
        total_roles = await credential_mapping.number_roles()
        start = page * count
        end = start + count
        end = min(end, total_roles)
        roles = roles[start:end]

        self.write(
            WebResponse(
                status=Status2.success,
                status_code=200,
                data=roles,
                page=page,
                total=total_roles,
                count=len(roles),
                last_page=_get_last_page(total_roles, count),
            ).json(exclude_unset=True)
        )


class AuditRolesAccessHandler(BaseMtlsHandler):
    """Handler for /api/v2/audit/roles/{accountNumber}/{roleName}/access

    Returns a list of groups with access to the requested role
    """

    allowed_methods = ["GET"]

    def check_xsrf_cookie(self) -> None:
        pass

    async def get(self, account_id, role_name):
        """
        GET /api/v2/audit/roles/{accountNumber}/{roleName}/access
        """
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "account_id": account_id,
            "role_name": role_name,
        }
        app_name = self.requester.get("name") or self.requester.get("username")
        stats.count(
            "RoleAccessHandler.get",
            tags={
                "requester": app_name,
                "account_id": account_id,
                "role_name": role_name,
            },
        )

        groups = await credential_mapping.determine_role_authorized_groups(
            account_id, role_name
        )
        if not groups:
            log_data[
                "message"
            ] = f"No authorized groups found for {role_name} in {account_id}"
            log.warning(log_data)
            self.set_status(404)
            self.write(
                WebResponse(
                    status=Status2.error,
                    status_code=404,
                    message="No groups found for requested role",
                ).json(exclude_unset=True)
            )
            return

        self.write(
            WebResponse(status=Status2.success, status_code=200, data=groups).json(
                exclude_unset=True
            )
        )

from asgiref.sync import sync_to_async
from cloudaux.aws.iam import get_role_managed_policy_documents

from consoleme.config import config
from consoleme.exceptions.exceptions import MustBeFte
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.models import WebResponse

log = config.get_logger()


class ManagedPoliciesOnRoleHandler(BaseAPIV2Handler):
    """
    Handler for /api/v2/managed_policies_on_role/{accountNumber}/{roleName}

    Returns managed policy and latest policy version information for a role
    """

    async def get(self, account_id, role_name):
        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")

        log_data = {
            "function": "ManagedPoliciesOnRoleHandler.get",
            "user": self.user,
            "ip": self.ip,
            "message": "Retrieving managed policies for role",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "account_id": account_id,
            "role_name": role_name,
        }

        log.debug(log_data)

        managed_policy_details = await sync_to_async(get_role_managed_policy_documents)(
            {"RoleName": role_name},
            account_number=account_id,
            assume_role=config.get("policies.role_name"),
            region=config.region,
        )
        res = WebResponse(
            status="success",
            status_code=200,
            data=managed_policy_details,
        )
        self.write(res.json())

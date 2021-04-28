from consoleme.config import config
from consoleme.exceptions.exceptions import MustBeFte
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.lib.aws import get_scps_for_account_or_ou


class ServiceControlPolicyHandler(BaseAPIV2Handler):
    allowed_methods = ["GET"]

    async def get(self, identifier):
        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                    "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")
        scps = await get_scps_for_account_or_ou(identifier)
        return scps.json()

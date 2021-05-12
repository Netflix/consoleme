import sentry_sdk

from consoleme.config import config
from consoleme.exceptions.exceptions import MustBeFte
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.lib.aws import get_scps_for_account_or_ou
from consoleme.models import Status2, WebResponse

log = config.get_logger()


class ServiceControlPolicyHandler(BaseAPIV2Handler):
    """
    Handler for /api/v2/service_control_policies/{accountNumberOrOuId}

    Returns Service Control Policies targeting specified account or OU
    """

    allowed_methods = ["GET"]

    async def get(self, identifier):
        if config.get("policy_editor.disallow_contractors", True) and self.contractor:
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")

        log_data = {
            "function": "ServiceControlPolicyHandler.get",
            "user": self.user,
            "message": "Retrieving service control policies for identifier",
            "identifier": identifier,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }

        log.debug(log_data)
        try:
            scps = await get_scps_for_account_or_ou(identifier)
        except Exception as e:
            sentry_sdk.capture_exception()
            response = WebResponse(
                status=Status2.error, status_code=403, errors=[str(e)], data=[]
            )
            self.write(response.json())
            return
        response = WebResponse(
            status=Status2.success, status_code=200, data=scps.__root__
        )
        self.write(response.json())

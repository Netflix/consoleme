from consoleme.config import config
from consoleme.handlers.base import BaseAPIV2Handler


class SelfServiceConfigHandler(BaseAPIV2Handler):
    allowed_methods = ["GET"]

    async def get(self):
        self.write(config.get("self_service_iam"))

from consoleme.handlers.base import BaseAPIV2Handler


class ServiceControlPolicyHandler(BaseAPIV2Handler):
    allowed_methods = ["GET"]

    async def get(self):
        pass

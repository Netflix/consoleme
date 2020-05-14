from consoleme.models.base_models import ExtendedRequestModel
from consoleme.models.base_models import RequestModel


class Request(ExtendedRequestModel):
    def __init__(self, *args, **kwargs):
        super().__init__(self)

    def store(self, dynamodb_client):
        """save to dynamodb"""
        pass

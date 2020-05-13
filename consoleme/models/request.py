from consoleme.models.models import ExtendedRequestModel
from consoleme.models.models import RequestModel


class Request(ExtendedRequestModel):
    def __init__(self, *args, **kwargs):
        super().__init__(self)

    def store(self):
        """save to dynamodb"""
        pass

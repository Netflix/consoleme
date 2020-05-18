from consoleme.models.base_models import CommentModel
from consoleme.models.base_models import ExtendedRequestModel
from consoleme.models.base_models import RequestModel


# Putting Comment here since it is only used in the context of Requests
class Comment(CommentModel):
    def __init__(self, *args, **kwargs):
        super().__init__(self)


class Request(ExtendedRequestModel):
    def __init__(self, *args, **kwargs):
        super().__init__(self)

    def store(self, dynamodb_client):
        """save to dynamodb"""
        pass

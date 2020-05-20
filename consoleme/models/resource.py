from consoleme.models.models import ResourceModel


class Resource(ResourceModel):
    def __init__(self, *args, **kwargs):
        super().__init__(self)

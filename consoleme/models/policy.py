from consoleme.models.base_models import PolicyModel


class Policy(PolicyModel):
    def __init__(self, *args, **kwargs):
        super().__init__(self)

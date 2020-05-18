from consoleme.models.base_models import ChangeModel
from consoleme.models.base_models import InlinePolicyChangeModel
from consoleme.models.base_models import ManagedPolicyChangeModel
from consoleme.models.base_models import ResourcePolicyChangeModel


class Change(ChangeModel):
    def __init__(self, *args, **kwargs):
        super().__init__(self)

    def store(self):
        """save to dynamodb"""
        pass


class InlinePolicyChange(InlinePolicyChangeModel):
    def __init__(self, *args, **kwargs):
        super().__init__(self)


class ManagedPolicyChange(ManagedPolicyChangeModel):
    def __init__(self, *args, **kwargs):
        super().__init__(self)


class ResourcePolicyChange(ResourcePolicyChangeModel):
    def __init__(self, *args, **kwargs):
        super().__init__(self)

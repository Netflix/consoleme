from consoleme.models.base_models import ExtendedRoleModel
from consoleme.models.base_models import RoleModel


class Role(ExtendedRoleModel):
    def __init__(self, *args, **kwargs):
        super().__init__(self)

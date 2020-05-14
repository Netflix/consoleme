from consoleme.models.models import UserModel


class User(UserModel):
    def __init__(self, *args, **kwargs):
        super().__init__(self)

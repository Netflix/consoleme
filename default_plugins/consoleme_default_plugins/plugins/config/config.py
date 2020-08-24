import os


class Config:
    @staticmethod
    def get_config_location():
        if os.environ.get("CONFIG_LOCATION"):
            return os.environ.get("CONFIG_LOCATION")
        path = "example_config/example_config_test.yaml"
        return path

    @staticmethod
    def internal_functions(cfg=None):
        cfg = cfg or {}
        pass

    @staticmethod
    def is_contractor(user):
        return False

    @staticmethod
    def get_employee_photo_url(user):
        return None

    @staticmethod
    def get_employee_info_url(user):
        return None


def init():
    """Initialize the Config plugin."""
    return Config()

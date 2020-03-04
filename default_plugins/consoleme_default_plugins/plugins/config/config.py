import os


class Config:
    @staticmethod
    def get_config_location():
        if os.environ.get("CONFIG_LOCATION"):
            return os.environ.get("CONFIG_LOCATION")
        path = "docker/example_config_test.yaml"
        return path

    @staticmethod
    def internal_functions(cfg=None):
        cfg = cfg or {}
        pass

    @staticmethod
    def is_contractor(user):
        return False


def init():
    """Initialize the Config plugin."""
    return Config()

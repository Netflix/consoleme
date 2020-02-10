import os


class Config:
    @staticmethod
    def get_config_location():
        load_config_paths = [
            os.path.join(os.getcwd(), "config.yaml"),
            "/etc/consoleme/config.yaml",
            "/apps/consoleme/config.yaml",
            "docker/example_config_test.yaml",
        ]
        for path in load_config_paths:
            if os.path.exists(path):
                return path
        raise Exception(
            f"Unable to find ConsoleMe Config file. Search locations: {', '.join(load_config_paths)}"
        )

    @staticmethod
    def internal_functions(cfg={}):
        pass

    @staticmethod
    def is_contractor(user):
        return False


def init():
    """Initialize the Config plugin."""
    return Config()

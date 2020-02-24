class Policies:
    """
    Policies internal plugin
    """

    def error_count_by_arn(self):
        return {}


def init():
    """Initialize Policies plugin."""
    return Policies()

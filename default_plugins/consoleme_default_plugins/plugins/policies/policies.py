class Policies:
    """
    Policies internal plugin
    """

    def error_count_by_arn(self):
        return {}

    async def get_errors_by_role(self, arn, n=5):
        return {}


def init():
    """Initialize Policies plugin."""
    return Policies()

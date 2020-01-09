class Policies:
    """
    Policies default plugin
    """

    async def get_errors_by_role(self, arn: str, n: int = 5):
        return []

    def error_count_by_arn(self):
        return {}


def init():
    """Initialize Policies plugin."""
    return Policies()

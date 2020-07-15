from consoleme.config import config
from consoleme.models import AppDetailsArray, AppDetailsModel


class Policies:
    """
    Policies internal plugin
    """

    def error_count_by_arn(self):
        return {}

    async def get_errors_by_role(self, arn, n=5):
        return {}

    async def get_applications_associated_with_role(self, arn: str) -> AppDetailsArray:
        """
        This function returns applications associated with a role from configuration. You may want to override this
        function to pull this information from an authoratative source.

        :param arn: Role ARN
        :return: AppDetailsArray
        """

        apps_formatted = []

        application_details = config.get("application_details", {})

        for app, details in application_details.items():
            apps_formatted.append(
                AppDetailsModel(
                    name=app,
                    owner=details.get("owner"),
                    owner_url=details.get("owner_url"),
                    app_url=details.get("app_url"),
                )
            )
        return AppDetailsArray(app_details=apps_formatted)


def init():
    """Initialize Policies plugin."""
    return Policies()

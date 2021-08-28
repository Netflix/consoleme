import sentry_sdk

from consoleme.config import config
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.lib.notifications.models import ConsoleMeNotificationUpdateRequest
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.lib.v2.notifications import get_notifications_for_user
from consoleme.models import Status2, WebResponse

stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
log = config.get_logger()


class NotificationsHandler(BaseAPIV2Handler):
    """
    A web handler for serving, updating, and (in the future) creating notifications. Current notifications are based
    around policy generation from CloudTrail errors.
    """

    async def get(self):
        try:
            # Check notifications for user, return notifications for user
            notifications = await get_notifications_for_user(self.user, self.groups)
            # TODO: Actually get the unread count instead of total count
            unread_count = len(notifications)
            response = WebResponse(
                status="success",
                status_code=200,
                data={
                    "unreadNotificationCount": unread_count,
                    "notifications": notifications,
                },
            )
            self.write(response.json())
        except Exception as e:
            sentry_sdk.capture_exception()
            self.set_status(500)
            response = WebResponse(
                status=Status2.error, status_code=500, errors=[str(e)], data=[]
            )
            self.write(response.json())
            return

    async def post(self):
        # Create a notification
        raise NotImplementedError()

    async def put(self):
        # Update a notification to be read or deleted
        # TODO: Use the `user_notification_settings` set  on the notification to update the status of the notification.
        change = ConsoleMeNotificationUpdateRequest.parse_raw(self.request.body)
        print(change)
        # TODO: Validate user is authorized to make the change
        # TODO:  Set the change in DB
        # TODO: Re-cache to Redis

from consoleme.handlers.base import BaseAPIV2Handler

# TODO: Move this
from consoleme.lib.v2.notifications import get_notifications_for_user
from consoleme.models import WebResponse


class NotificationsHandler(BaseAPIV2Handler):
    """
    A class for receiving notifications. These usually consist of Cloudtrail errors, but it could really be anything.
    """

    async def get(self):
        # TODO: Allow selectively enrolling users / groups for notifications so we can shard this out
        # Check notifications for user, return notifications for user
        notifications = await get_notifications_for_user(self.user, self.groups)
        # TODO: Actually get the unread count instead of total count
        unread_count = len(notifications)
        # TODO: Try/except and non-200 status
        response = WebResponse(
            status="success",
            status_code=200,
            data={
                "unreadNotificationCount": unread_count,
                "notifications": notifications,
            },
        )
        self.write(response.json())

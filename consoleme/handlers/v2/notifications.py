import sentry_sdk

from consoleme.config import config
from consoleme.handlers.base import BaseAPIV2Handler
from consoleme.lib.generic import is_in_group
from consoleme.lib.notifications.models import (
    ConsoleMeNotificationUpdateAction,
    ConsoleMeNotificationUpdateRequest,
)
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
        """
        Allows an "authorized user" (Any user the notification is intended for) to mark the notification as read/unread
        or hidden/unhidden for themselves or all other notification recipients

        :return:
        """
        change = ConsoleMeNotificationUpdateRequest.parse_raw(self.request.body)
        errors = []

        for notification in change.notifications:
            authorized = is_in_group(
                self.user, self.groups, notification.users_or_groups
            )
            if not authorized:
                errors.append(
                    f"Unauthorized because user is not associated with notification: {notification.predictable_id}"
                )
                continue
            if (
                change.action
                == ConsoleMeNotificationUpdateAction.toggle_read_for_current_user
            ):
                if self.user in notification.read_by_users:
                    # Mark as unread
                    notification.read_by_users.remove(self.user)
                else:
                    # Mark as read
                    notification.read_by_users.append(self.user)
            elif (
                change.action
                == ConsoleMeNotificationUpdateAction.toggle_read_for_all_users
            ):
                if notification.read_by_all:
                    # Mark as "Read by all"
                    notification.read_by_all = False
                else:
                    # Unmark as "Read by all" (Falls back to `notification.read_by_user` to determine if
                    # users have read the notification
                    notification.read_by_all = True
            elif (
                change.action
                == ConsoleMeNotificationUpdateAction.toggle_hidden_for_current_user
            ):
                if self.user in notification.hidden_for_users:
                    # Unmark as hidden
                    notification.hidden_for_users.remove(self.user)
                else:
                    # Mark as hidden
                    notification.hidden_for_users.append(self.user)
            elif (
                change.action
                == ConsoleMeNotificationUpdateAction.toggle_hidden_for_all_users
            ):
                if notification.hidden_for_all:
                    # Mark as "Hidden for all users"
                    notification.hidden_for_all = False
                else:
                    # Unmark as "Hidden for all users" (Falls back to `hidden_for_users.read_by_user` to determine
                    # whether to show the notification or not
                    notification.hidden_for_all = True
            print(notification)
        # TODO:  Set the change in DB
        # TODO: Re-cache to Redis
        # TODO: Reuse this in separate function
        try:
            # Check notifications for user, return notifications for user
            notifications = await get_notifications_for_user(
                self.user, self.groups, force_refresh=True
            )
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

import time

import sentry_sdk
import ujson as json

from consoleme.config import config
from consoleme.lib.cache import retrieve_json_data_from_redis_or_s3
from consoleme.lib.notifications.models import ConsoleMeUserNotification
from consoleme.lib.singleton import Singleton

# TODO: Use notification version specification to ignore older versions


class RetrieveNotifications(metaclass=Singleton):
    def __init__(self):
        self.last_update = 0
        self.all_notifications = []

    async def retrieve_all_notifications(self, force_refresh=False):
        if force_refresh or (
            int(time.time()) - self.last_update
            > config.get(
                "get_notifications_for_user.notification_retrieval_interval", 20
            )
        ):
            self.all_notifications = await retrieve_json_data_from_redis_or_s3(
                redis_key=config.get("notifications.redis_key", "ALL_NOTIFICATIONS"),
                redis_data_type="hash",
                s3_bucket=config.get("notifications.s3.bucket"),
                s3_key=config.get(
                    "notifications.s3.key", "notifications/all_notifications_v1.json.gz"
                ),
            )
            self.last_update = int(time.time())
        return self.all_notifications


async def get_notifications_for_user(
    user,
    groups,
    max_notifications=config.get("get_notifications_for_user.max_notifications", 5),
    force_refresh=False,
):

    current_time = int(time.time())
    all_notifications = await RetrieveNotifications().retrieve_all_notifications(
        force_refresh
    )

    notifications_for_user_raw = json.loads(all_notifications.get(user, "[]"))
    notifications_for_user = []
    for notification in notifications_for_user_raw:
        notifications_for_user.append(ConsoleMeUserNotification.parse_obj(notification))
    for group in groups:
        # Filter out identical notifications that were already captured via user-specific attribution. IE: "UserA"
        # performed an access deny operation locally under "RoleA" with session name = "UserA", so the generated
        # notification is tied to the user. However, "UserA" is a member of "GroupA", which owns RoleA. We want
        # to show the notification to members of "GroupA", as well as "UserA" but we don't want "UserA" to see 2
        # notifications.
        notifications = all_notifications.get(group)
        if not notifications:
            continue
        notifications = json.loads(notifications)
        for notification_raw in notifications:
            try:
                # We parse ConsoleMeUserNotification individually instead of as an array
                # to account for future changes to the model that may invalidate older
                # notifications
                notification = ConsoleMeUserNotification.parse_obj(notification_raw)
            except:
                sentry_sdk.capture_exception()
                continue
            if notification.version != 1:
                # Skip unsupported versions of the notification model
                continue
            if user in notification.hidden_for_users:
                # Skip this notification if it isn't hidden for the user
                continue
            seen = False
            for existing_user_notification_raw in notifications_for_user:
                existing_user_notification = ConsoleMeUserNotification.parse_obj(
                    existing_user_notification_raw
                )
                if (
                    notification.predictable_id
                    == existing_user_notification.predictable_id
                ):
                    seen = True
            if not seen:
                notifications_for_user.append(notification)
    # Filter out "expired" notifications
    notifications_for_user = [
        v for v in notifications_for_user if v.expiration > current_time
    ]
    # Show newest notifications first
    notifications_for_user = sorted(
        notifications_for_user, key=lambda i: i.event_time, reverse=True
    )
    return notifications_for_user[0:max_notifications]

import time

import ujson as json

from consoleme.config import config
from consoleme.lib.cache import retrieve_json_data_from_redis_or_s3
from consoleme.lib.singleton import Singleton


class RetrieveNotifications(metaclass=Singleton):
    def __init__(self):
        self.last_update = 0
        self.all_notifications = []

    async def retrieve_all_notifications(self):
        if int(time.time()) - self.last_update > config.get(
            "get_notifications_for_user.notification_retrieval_interval", 20
        ):
            self.all_notifications = await retrieve_json_data_from_redis_or_s3(
                redis_key=config.get("notifications.redis_key", "ALL_NOTIFICATIONS"),
                redis_data_type="hash",
                s3_bucket=config.get("notifications.s3.bucket"),
                s3_key=config.get(
                    "notifications.s3.key", "notifications/all_notifications_v1.json.gz"
                ),
            )
        return self.all_notifications


async def get_notifications_for_user(
    user,
    groups,
    max_notifications=config.get("get_notifications_for_user.max_notifications", 5),
):

    current_time = int(time.time())
    all_notifications = await RetrieveNotifications().retrieve_all_notifications()

    notifications_for_user = []
    if all_notifications.get(user):
        notifications_for_user.extend(json.loads(all_notifications[user]))
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
        for notification in notifications:
            seen = False
            for existing_user_notification in notifications_for_user:
                if (
                    notification["predictable_id"]
                    == existing_user_notification["predictable_id"]
                ):
                    seen = True
            if not seen:
                notifications_for_user.append(notification)
    # Filter out "expired" notifications
    notifications_for_user = [
        v for v in notifications_for_user if v["expiration"] > current_time
    ]
    # Show newest notifications first
    notifications_for_user = sorted(
        notifications_for_user, key=lambda i: i["event_time"], reverse=True
    )
    return notifications_for_user[0:max_notifications]

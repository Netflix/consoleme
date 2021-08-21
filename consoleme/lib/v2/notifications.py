import time

import ujson as json

from consoleme.config import config
from consoleme.lib.cache import retrieve_json_data_from_redis_or_s3


async def get_notifications_for_user(
    user,
    groups,
    max_notifications=config.get("get_notifications_for_user.max_notifications", 5),
):
    current_time = int(time.time())
    # TODO: Only load once every N seconds. Singleton?
    all_notifications = await retrieve_json_data_from_redis_or_s3(
        redis_key=config.get("notifications.redis_key", "ALL_NOTIFICATIONS"),
        redis_data_type="hash",
        s3_bucket=config.get("notifications.s3.bucket"),
        s3_key=config.get(
            "notifications.s3.key", "notifications/all_notifications_v1.json.gz"
        ),
    )

    notifications_for_user = []
    if all_notifications.get(user):
        notifications_for_user.extend(json.loads(all_notifications[user]))
    for group in groups:
        if all_notifications.get(group):
            notifications_for_user.extend(json.loads(all_notifications[group]))
    notifications_for_user = [
        v for v in notifications_for_user if v["expiration"] > current_time
    ]
    notifications_for_user = sorted(
        notifications_for_user, key=lambda i: i["event_time"], reverse=True
    )
    return notifications_for_user[0:max_notifications]

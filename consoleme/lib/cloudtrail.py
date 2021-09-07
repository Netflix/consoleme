import base64
import json as original_json
import time
from collections import defaultdict

import simplejson as json
from boto3.dynamodb.types import Binary  # noqa

from consoleme.config import config
from consoleme.lib.aws import get_iam_principal_owner, simulate_iam_principal_action
from consoleme.lib.cache import store_json_results_in_redis_and_s3
from consoleme.lib.dynamo import UserDynamoHandler
from consoleme.lib.json_encoder import SetEncoder
from consoleme.lib.notifications.models import (
    ConsoleMeUserNotification,
    ConsoleMeUserNotificationAction,
)

ddb = UserDynamoHandler()


class CloudTrail:
    async def process_cloudtrail_errors(
        self,
        aws,
        notification_ttl_seconds=config.get(
            "process_cloudtrail_errors.notification_ttl", 86400
        ),
    ) -> object:
        """
        Processes Cloudtrail Errors that were cached by the `cache_cloudtrail_denies` celery task. Generates and returns
        count data. If configured, generates notifications to end-users based on policies that can be generated

        :param notification_ttl_seconds:
        :return:
        """
        notification_type = "cloudtrail_generated_policy"
        expiration = int(time.time() + notification_ttl_seconds)

        # Get all existing cloudtrail_generated_policy notifications
        all_notifications = {}
        all_notifications_l = await ddb.parallel_scan_table_async(
            ddb.notifications_table
        )
        for existing_notification in all_notifications_l:
            if existing_notification["type"] != notification_type:
                continue
            all_notifications[
                existing_notification["predictable_id"]
            ] = ConsoleMeUserNotification.parse_obj(existing_notification)

        error_count = {}
        # Get all existing Cloudtrail errors. This will be expensive if there are a large number of errors.
        cloudtrail_errors = await ddb.parallel_scan_table_async(
            ddb.cloudtrail_table,
        )
        cloudtrail_errors = ddb._data_from_dynamo_replace(cloudtrail_errors)
        error_count = ddb.count_arn_errors(error_count, cloudtrail_errors)
        new_or_changed_notifications = {}
        for cloudtrail_error in cloudtrail_errors:
            arn = cloudtrail_error.get("arn", "")
            principal_owner = await get_iam_principal_owner(arn, aws)
            session_name = cloudtrail_error.get("session_name", "")
            principal_type = "iam" + arn.split(":")[-1].split("/")[0]
            account_id = arn.split(":")[4]
            principal_name = arn.split("/")[-1]
            url_role_path = (
                f"/policies/edit/{account_id}/{principal_type}/{principal_name}"
            )
            event_call = cloudtrail_error.get("event_call", "")
            resource = cloudtrail_error.get("resource", "")
            # If a given IAM principal encounters an sts:AssumeRole AccessDeny error for a given role across multiple
            # accounts (I.E. The role being assumed has the same name on multiple accounts), we only want to generate
            # one notification for the issue. Therefore, resource_full_name might not accurately reflect the resource
            # name, but it works for the purposes of creating a unique ID such that only one notification gets created
            # for this set of CloudTrail Events
            resource_full_name = resource.split(":")[-1]
            predictable_id = f"{notification_type}-{principal_owner}-{principal_name}-{event_call}-{resource_full_name}"
            generated_request = {
                "role": {
                    "name": principal_name,
                    "account_id": account_id,
                    "account_name": "",
                    "arn": arn,
                    "cloudtrail_details": {
                        "error_url": "",
                        "errors": {
                            "cloudtrail_errors": [],
                        },
                    },
                    "s3_details": {
                        "error_url": "",
                        "errors": {
                            "s3_errors": [],
                        },
                    },
                    "apps": {
                        "app_details": [],
                    },
                    "tags": [],
                    "templated": False,
                    "principal": {
                        "principal_type": "AwsResource",
                        "principal_arn": arn,
                    },
                },
                "updated_policy": json.dumps(cloudtrail_error["generated_policy"]),
            }
            encoded_request = base64.b64encode(
                json.dumps(generated_request).encode()
            ).decode("utf-8")
            encoded_request_url = f"/selfservice?encoded_request={encoded_request}"
            notification_message = config.get(
                "process_cloudtrail_errors.generate_notifications.message",
                """We've generated a policy suggestion for a recent permissions error with **[{arn}]({url_role_path})**.
Please click the button below to review it.

You are receiving this notification because your team owns this role, or you were using this role at the time the error
was detected. This notification will disappear when a similar error has not occurred for 24 hours.""".format(
                    arn=arn,
                    url_role_path=url_role_path,
                ),
            )

            message_actions = [
                ConsoleMeUserNotificationAction.parse_obj(
                    {
                        "http_method": "get",
                        "uri": encoded_request_url,
                        "text": "Review and Submit Request",
                    }
                )
            ]

            generated_notification = ConsoleMeUserNotification(
                predictable_id=predictable_id,
                type=notification_type,
                users_or_groups=set(),
                event_time=cloudtrail_error["epoch_event_time"],
                expiration=expiration,
                expired=False,
                message=notification_message,
                message_actions=message_actions,
                details=cloudtrail_error,
                read_by_users=set(),
                read_by_all=False,
                hidden_for_users=set(),
                hidden_for_all=False,
                version=1,
            )

            # Update existing item without overwriting settings
            if all_notifications.get(predictable_id):
                new_or_changed_notifications[predictable_id] = all_notifications[
                    predictable_id
                ]
                new_or_changed_notifications[
                    predictable_id
                ].event_time = cloudtrail_error["epoch_event_time"]
                new_or_changed_notifications[predictable_id].expiration = expiration
                new_or_changed_notifications[predictable_id].expired = False
                new_or_changed_notifications[
                    predictable_id
                ].message = notification_message
                new_or_changed_notifications[predictable_id].details = cloudtrail_error
            else:
                # Maybe Add IAM policy simulation result to the CloudTrail event, and in turn, the notification details
                # We don't want to simulate events for every single update of a notification, just one time for
                # Initial creation
                if config.get(
                    "process_cloudtrail_errors.simulate_iam_principal_action"
                ):
                    generated_notification.details[
                        "iam_policy_simulation"
                    ] = await simulate_iam_principal_action(
                        arn, event_call, resource, cloudtrail_error.get("source_ip")
                    )
            if principal_owner and not all_notifications.get(predictable_id):
                generated_notification.users_or_groups.add(principal_owner)
                new_or_changed_notifications[predictable_id] = generated_notification

            # Also link Notifications with users via session nme
            if not session_name or session_name.startswith(
                "i-"
            ):  # Session ID is instance ID
                continue

            if new_or_changed_notifications.get(predictable_id):
                new_or_changed_notifications[predictable_id].users_or_groups.add(
                    session_name
                )
            else:
                new_or_changed_notifications[predictable_id] = generated_notification
                new_or_changed_notifications[predictable_id].users_or_groups.add(
                    session_name
                )

            # Optionally add development users to the notification
            new_or_changed_notifications[predictable_id].users_or_groups.update(
                set(config.get("process_cloudtrail_errors.additional_notify_users", []))
            )
        new_or_changed_notifications_l = []
        notifications_by_user_group = defaultdict(list)
        for notification in new_or_changed_notifications.values():
            new_or_changed_notifications_l.append(notification.dict())
            for user_or_group in notification.users_or_groups:
                notifications_by_user_group[user_or_group].append(notification.dict())
        if new_or_changed_notifications_l:
            ddb.parallel_write_table(
                ddb.notifications_table, new_or_changed_notifications_l
            )
        if notifications_by_user_group:
            for k, v in notifications_by_user_group.items():
                notifications_by_user_group[k] = original_json.dumps(v, cls=SetEncoder)
            await store_json_results_in_redis_and_s3(
                notifications_by_user_group,
                redis_key=config.get("notifications.redis_key", "ALL_NOTIFICATIONS"),
                redis_data_type="hash",
                s3_bucket=config.get("notifications.s3.bucket"),
                s3_key=config.get(
                    "notifications.s3.key", "notifications/all_notifications_v1.json.gz"
                ),
            )
        return {
            "error_count_by_role": error_count,
            "num_new_or_changed_notifications": len(new_or_changed_notifications_l),
        }

from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import Field

from consoleme.lib.pydantic import BaseModel


class ConsoleMeUserNotificationAction(BaseModel):
    http_method: str = Field(
        ..., description="HTTP method for the request", example="get"
    )
    uri: str = Field(
        ..., description="URL to send the request if user invokes the action"
    )
    text: str = Field(..., description="Text to show for the call-to-action")


class ConsoleMeUserNotification(BaseModel):
    predictable_id: str = Field(
        ...,
        description=(
            "Predictable ID for this notification. Generally used to prevent duplicate notifications"
        ),
    )
    type: str = Field(
        ...,
        description=(
            "Each class of notification should be given a separate type, "
            "IE: `cloudtrail_generated_policy` or `proxy_generated_policy"
        ),
    )
    users_or_groups: Set[str] = Field(
        ..., description="Users or groups who should see the notification"
    )
    event_time: int = Field(..., description="Time that the event took place")
    expiration: int = Field(
        ..., description="Time that this entry should stop notifying people"
    )
    expired: bool = Field(
        ...,
        description="A more obvious indicator about whether a notification has expired",
    )
    header: Optional[str] = Field(
        None, description="Bolded text (Header) for the notification"
    )
    message: str = Field(
        ...,
        description="An (optionally markdown) formatted message to show to users in the UI",
    )
    message_actions: List[ConsoleMeUserNotificationAction] = Field(
        ...,
        description=(
            "An optional list of actions to make available to the user. These will be shown below the notification."
        ),
    )
    details: Dict[str, Any] = Field(
        ...,
        description=(
            "Extra details about the notification for power users. "
            "This will be accessible to the user in the UI, but not visible by default"
        ),
    )
    read_by_users: List[str] = Field(
        ...,
        description=(
            "List of users the notification is `read` for. It will show up in the user's list of notifications, "
            "but will not be shown as `unread` nor be included in the unread counter."
        ),
    )
    read_by_all: bool = Field(
        False,
        description=(
            "Notification is `marked as read` for all users and will not appear as an unread notification for "
            "any users."
        ),
    )
    hidden_for_users: List[str] = Field(
        ...,
        description=(
            "List of users the notification is `hidden` for. It will not appear at all in the user's list of "
            "notifications."
        ),
    )
    hidden_for_all: bool = Field(
        False,
        description=(
            "Notification is `marked as hidden` for all users, and will not appear in the notificaiton list for "
            "any user."
        ),
    )
    read_for_current_user: bool = Field(
        None,
        description=(
            "Convenience variable  to mark a notification as read for current user when retrieving notification. "
            "This makes it so the frontend doesn't need to do any computation to figure it out. A Non-None value "
            "should not be stored in the database."
        ),
    )
    version: int = Field(..., description=("Version of the notification model"))


class ConsoleMeNotificationUpdateAction(Enum):
    toggle_read_for_current_user = "toggle_read_for_current_user"
    toggle_read_for_all_users = "toggle_read_for_all_users"
    toggle_hidden_for_current_user = "toggle_hidden_for_current_user"
    toggle_hidden_for_all_users = "toggle_hidden_for_all_users"


class ConsoleMeNotificationUpdateRequest(BaseModel):
    action: ConsoleMeNotificationUpdateAction
    notifications: List[ConsoleMeUserNotification]


class GetNotificationsForUserResponse(BaseModel):
    notifications: List[ConsoleMeUserNotification]
    unread_count: int

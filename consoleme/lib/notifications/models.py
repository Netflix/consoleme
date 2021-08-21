from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field


class ConsoleMeNotificationSettings(BaseModel):
    marked_as_deleted: bool = Field(
        ...,
        description=(
            "Stop showing this notification, but keep it in the database. "
            "Users can choose to delete a notification for themselves, or everyone on their team."
        ),
    )
    read: bool = Field(..., description=("Mark the notification as read."))


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
    header: Optional[str] = Field(
        None, description="Bolded text (Header) for the notification"
    )
    message: str = Field(
        ...,
        description="An (optionally markdown) formatted message to show to users in the UI",
    )
    details: Dict[str, Any] = Field(
        ...,
        description=(
            "Extra details about the notification for power users. "
            "This will be accessible to the user in the UI, but not visible by default"
        ),
    )
    global_notification_settings: ConsoleMeNotificationSettings
    user_notification_settings: Dict[str, ConsoleMeNotificationSettings]

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import NotificationStatus, NotificationType


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_user_id: int
    trip_request_id: int | None
    trip_id: int | None
    type: NotificationType
    subject: str
    message: str
    status: NotificationStatus
    error_message: str | None
    created_at: datetime
    sent_at: datetime | None

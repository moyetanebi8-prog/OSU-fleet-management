from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AlertType


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int
    trip_id: int | None
    type: AlertType
    message: str
    timestamp: datetime
    is_read: bool

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import DriverStatus


class DriverCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    license_number: str = Field(min_length=1, max_length=64)
    # Optional at the DB level for backward compatibility with drivers
    # created before this field existed, but strongly recommended going
    # forward - a driver with no email can never receive a real trip
    # assignment notification (see notification_service.notify_trip_approved).
    email: EmailStr | None = None


class DriverUpdate(BaseModel):
    """Full replace of the editable fields. Status is intentionally NOT
    editable here - see DriverStatusUpdate / PATCH /drivers/{id}/status."""

    name: str = Field(min_length=1, max_length=128)
    license_number: str = Field(min_length=1, max_length=64)
    email: EmailStr | None = None


class DriverStatusUpdate(BaseModel):
    status: DriverStatus


class DriverResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    license_number: str
    email: str | None
    status: DriverStatus
    created_at: datetime

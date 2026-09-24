from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import VehicleStatus


class VehicleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    model: str | None = Field(default=None, max_length=128)
    plate_number: str = Field(min_length=1, max_length=32)
    capacity: int = Field(gt=0, le=100)


class VehicleUpdate(BaseModel):
    """Full replace of the editable fields. Status is intentionally NOT
    editable here - see VehicleStatusUpdate / PATCH /vehicles/{id}/status,
    which enforces valid manual transitions instead of accepting any value.
    """

    name: str = Field(min_length=1, max_length=128)
    model: str | None = Field(default=None, max_length=128)
    plate_number: str = Field(min_length=1, max_length=32)
    capacity: int = Field(gt=0, le=100)


class VehicleStatusUpdate(BaseModel):
    status: VehicleStatus


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    model: str | None
    plate_number: str
    capacity: int
    status: VehicleStatus
    created_at: datetime
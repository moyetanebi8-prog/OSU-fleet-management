from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PingCreate(BaseModel):
    """No `trip_id` and no `timestamp` field here on purpose: which trip (if
    any) a ping belongs to is decided server-side from the vehicle's
    current state (see app/services/gps_service.py), and the timestamp is
    always the server clock, never client-supplied."""

    vehicle_id: int
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    speed: float = Field(ge=0, le=300)


class PingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int
    trip_id: int | None
    lat: float
    lng: float
    speed: float
    timestamp: datetime

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TripStatus
from app.schemas.driver import DriverResponse
from app.schemas.vehicle import VehicleResponse


class AvailableResourcesResponse(BaseModel):
    """Response for GET /trip-requests/{id}/available-resources.
    Never "every vehicle/driver" - see trip_service.get_available_vehicles
    / get_available_drivers for the actual filtering (status + capacity +
    schedule-conflict checks)."""

    vehicles: list[VehicleResponse]
    drivers: list[DriverResponse]


class ApproveRequestPayload(BaseModel):
    vehicle_id: int
    driver_id: int


class DeclineRequestPayload(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class TripResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    vehicle_id: int
    driver_id: int
    status: TripStatus
    planned_start_time: datetime
    planned_end_time: datetime
    actual_start_time: datetime | None
    actual_end_time: datetime | None
    start_lat: float | None
    start_lng: float | None
    end_lat: float | None
    end_lng: float | None
    distance_km: float | None
    created_at: datetime

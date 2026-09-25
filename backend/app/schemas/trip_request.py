from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import TripRequestStatus
from app.models.trip_request import TripRequest
from app.schemas.user import UserSummary


TravelerSummary = UserSummary


class TripRequestCreate(BaseModel):
    """
    No requester_id and no status field here on purpose: the requester
    is always the authenticated caller, and every new request starts
    pending.

    passenger_count is derived server-side from the actual traveler list.

    traveler_ids contains the other employees traveling with the requester.
    The requester is added automatically.
    """

    purpose: str = Field(min_length=1, max_length=255)

    source: str = Field(min_length=1, max_length=255)
    source_lat: float | None = None
    source_lng: float | None = None

    destination: str = Field(min_length=1, max_length=255)
    destination_lat: float | None = None
    destination_lng: float | None = None

    requested_start: datetime
    requested_end: datetime

    traveler_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_time_window(self) -> "TripRequestCreate":
        if self.requested_end <= self.requested_start:
            raise ValueError("requested_end must be after requested_start.")
        return self


class TripRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requester_id: int
    requester_username: str
    purpose: str

    source: str
    source_lat: float | None
    source_lng: float | None

    destination: str
    destination_lat: float | None
    destination_lng: float | None

    requested_start: datetime
    requested_end: datetime
    passenger_count: int
    travelers: list[TravelerSummary]
    status: TripRequestStatus
    decline_reason: str | None
    trip_id: int | None
    created_at: datetime

    @classmethod
    def from_model(
        cls,
        trip_request: TripRequest,
    ) -> "TripRequestResponse":
        travelers = [
            TravelerSummary.model_validate(link.user)
            for link in trip_request.traveler_links
        ]

        return cls(
            id=trip_request.id,
            requester_id=trip_request.requester_id,
            requester_username=trip_request.requester.username,
            purpose=trip_request.purpose,

            source=trip_request.source,
            source_lat=trip_request.source_lat,
            source_lng=trip_request.source_lng,

            destination=trip_request.destination,
            destination_lat=trip_request.destination_lat,
            destination_lng=trip_request.destination_lng,

            requested_start=trip_request.requested_start,
            requested_end=trip_request.requested_end,
            passenger_count=trip_request.passenger_count,
            travelers=travelers,
            status=trip_request.status,
            decline_reason=trip_request.decline_reason,

            trip_id=(
                trip_request.trip.id
                if trip_request.trip is not None
                else None
            ),

            created_at=trip_request.created_at,
        )
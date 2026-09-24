from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import TripRequestStatus
from app.models.trip_request import TripRequest
from app.schemas.user import UserSummary

# Same shape as UserSummary - kept as a distinct name in this module so
# call sites read clearly ("a request's travelers" vs. "a user record"),
# without duplicating the field definitions.
TravelerSummary = UserSummary


class TripRequestCreate(BaseModel):
    """
    No `requester_id` and no `status` field here on purpose: the requester
    is always the authenticated caller (never client-supplied - see
    app/routers/trip_requests.py), and every new request starts `pending`.

    No `passenger_count` field either, on purpose: it's derived server-side
    from the actual traveler list (see trip_service.create_trip_request_with_
    travelers), never trusted as a raw number a client could set
    inconsistently with who's actually selected.

    `traveler_ids` should contain the OTHER employees traveling - the
    requester is added automatically and does not need to include their
    own id here (harmless if they do; duplicates collapse).
    """

    purpose: str = Field(min_length=1, max_length=255)
    destination: str = Field(min_length=1, max_length=255)
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
    destination: str
    requested_start: datetime
    requested_end: datetime
    passenger_count: int
    travelers: list[TravelerSummary]
    status: TripRequestStatus
    decline_reason: str | None
    trip_id: int | None
    created_at: datetime

    @classmethod
    def from_model(cls, trip_request: TripRequest) -> "TripRequestResponse":
        """Build the response explicitly rather than relying on
        from_attributes to guess a flattened `requester_username` field
        that doesn't exist on the ORM model - this stays simple even as
        the schema evolves.

        Expects `trip_request.traveler_links` to be loaded with each
        link's `.user` populated (see the eager-load in
        app/routers/trip_requests.py) - this does not issue additional
        queries itself."""
        travelers = [
            TravelerSummary.model_validate(link.user) for link in trip_request.traveler_links
        ]
        return cls(
            id=trip_request.id,
            requester_id=trip_request.requester_id,
            requester_username=trip_request.requester.username,
            purpose=trip_request.purpose,
            destination=trip_request.destination,
            requested_start=trip_request.requested_start,
            requested_end=trip_request.requested_end,
            passenger_count=trip_request.passenger_count,
            travelers=travelers,
            status=trip_request.status,
            decline_reason=trip_request.decline_reason,
            # `trip` is a one-to-one relationship, None until the request
            # is approved (see app/services/trip_service.approve_trip_request).
            # The frontend uses this to link a request to its resulting
            # trip without a second lookup.
            trip_id=trip_request.trip.id if trip_request.trip is not None else None,
            created_at=trip_request.created_at,
        )

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies.auth import (
    get_current_user,
    require_dispatcher,
    require_requester,
)
from app.models.enums import TripRequestStatus, UserRole
from app.models.trip_request import TripRequest
from app.models.trip_request_traveler import TripRequestTraveler
from app.models.user import User
from app.schemas.driver import DriverResponse
from app.schemas.trip import (
    ApproveRequestPayload,
    AvailableResourcesResponse,
    DeclineRequestPayload,
    TripResponse,
)
from app.schemas.trip_request import TripRequestCreate, TripRequestResponse
from app.schemas.vehicle import VehicleResponse
from app.services import trip_service
from app.services.geocoding_service import (
    GeocodingError,
    geocode_location,
)

router = APIRouter(prefix="/trip-requests", tags=["trip-requests"])


def _get_request_or_404(
    db: Session,
    request_id: int,
) -> TripRequest:
    trip_request = (
        db.query(TripRequest)
        .options(
            joinedload(TripRequest.requester),
            joinedload(TripRequest.traveler_links).joinedload(
                TripRequestTraveler.user
            ),
        )
        .filter(TripRequest.id == request_id)
        .first()
    )

    if trip_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip request not found.",
        )

    return trip_request


def _assert_can_view(
    trip_request: TripRequest,
    current_user: User,
) -> None:
    if current_user.role == UserRole.DISPATCHER:
        return

    if trip_request.requester_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own trip requests.",
        )


@router.post(
    "/",
    response_model=TripRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_trip_request(
    payload: TripRequestCreate,
    current_user: User = Depends(require_requester),
    db: Session = Depends(get_db),
) -> TripRequestResponse:

    # Convert the locations entered by the requester into coordinates.
    # No locations are hard-coded here.
    try:
        source_lat, source_lng = await geocode_location(
            payload.source
        )

        destination_lat, destination_lng = await geocode_location(
            payload.destination
        )

    except GeocodingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    try:
        trip_request = trip_service.create_trip_request_with_travelers(
            db,
            current_user,
            purpose=payload.purpose,
            source=payload.source,
            source_lat=source_lat,
            source_lng=source_lng,
            destination=payload.destination,
            destination_lat=destination_lat,
            destination_lng=destination_lng,
            requested_start=payload.requested_start,
            requested_end=payload.requested_end,
            traveler_ids=payload.traveler_ids,
        )

    except trip_service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except trip_service.InvalidStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # Re-fetch with the eager-loads needed by from_model().
    trip_request = _get_request_or_404(
        db,
        trip_request.id,
    )

    return TripRequestResponse.from_model(trip_request)


@router.get(
    "/",
    response_model=list[TripRequestResponse],
)
def list_trip_requests(
    status_filter: TripRequestStatus | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TripRequestResponse]:
    """
    Dispatchers see every request.
    Requesters see only their own requests.
    """

    query = db.query(TripRequest).options(
        joinedload(TripRequest.requester),
        joinedload(TripRequest.traveler_links).joinedload(
            TripRequestTraveler.user
        ),
    )

    if current_user.role != UserRole.DISPATCHER:
        query = query.filter(
            TripRequest.requester_id == current_user.id
        )

    if status_filter is not None:
        query = query.filter(
            TripRequest.status == status_filter
        )

    trip_requests = (
        query
        .order_by(TripRequest.created_at.desc())
        .all()
    )

    return [
        TripRequestResponse.from_model(tr)
        for tr in trip_requests
    ]


@router.get(
    "/{request_id}",
    response_model=TripRequestResponse,
)
def get_trip_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TripRequestResponse:

    trip_request = _get_request_or_404(
        db,
        request_id,
    )

    _assert_can_view(
        trip_request,
        current_user,
    )

    return TripRequestResponse.from_model(
        trip_request
    )


@router.get(
    "/{request_id}/available-resources",
    response_model=AvailableResourcesResponse,
    dependencies=[Depends(require_dispatcher)],
)
def get_available_resources(
    request_id: int,
    db: Session = Depends(get_db),
) -> AvailableResourcesResponse:

    trip_request = _get_request_or_404(
        db,
        request_id,
    )

    vehicles = trip_service.get_available_vehicles(
        db,
        trip_request,
    )

    drivers = trip_service.get_available_drivers(
        db,
        trip_request,
    )

    return AvailableResourcesResponse(
        vehicles=[
            VehicleResponse.model_validate(v)
            for v in vehicles
        ],
        drivers=[
            DriverResponse.model_validate(d)
            for d in drivers
        ],
    )


@router.post(
    "/{request_id}/approve",
    response_model=TripResponse,
    dependencies=[Depends(require_dispatcher)],
)
def approve_trip_request(
    request_id: int,
    payload: ApproveRequestPayload,
    db: Session = Depends(get_db),
) -> TripResponse:

    try:
        trip = trip_service.approve_trip_request(
            db,
            request_id,
            payload.vehicle_id,
            payload.driver_id,
        )

    except trip_service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except trip_service.InvalidStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except trip_service.ConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return TripResponse.model_validate(trip)


@router.post(
    "/{request_id}/decline",
    response_model=TripRequestResponse,
    dependencies=[Depends(require_dispatcher)],
)
def decline_trip_request(
    request_id: int,
    payload: DeclineRequestPayload,
    db: Session = Depends(get_db),
) -> TripRequestResponse:

    try:
        trip_request = trip_service.decline_trip_request(
            db,
            request_id,
            payload.reason,
        )

    except trip_service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except trip_service.InvalidStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return TripRequestResponse.from_model(
        trip_request
    )
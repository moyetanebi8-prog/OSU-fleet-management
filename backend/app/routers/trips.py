from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies.auth import get_current_user, require_dispatcher
from app.models.enums import UserRole
from app.models.location_ping import LocationPing
from app.models.trip import Trip
from app.models.trip_request import TripRequest
from app.models.user import User
from app.schemas.ping import PingResponse
from app.schemas.trip import TripResponse
from app.services import trip_service

router = APIRouter(prefix="/trips", tags=["trips"])


def _get_trip_or_404(db: Session, trip_id: int) -> Trip:
    trip = (
        db.query(Trip)
        .options(joinedload(Trip.request))
        .filter(Trip.id == trip_id)
        .first()
    )
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found.")
    return trip


def _assert_can_view(trip: Trip, current_user: User) -> None:
    if current_user.role == UserRole.DISPATCHER:
        return
    if trip.request.requester_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view trips created from your own requests.",
        )


def _map_service_error(exc: trip_service.TripServiceError) -> HTTPException:
    if isinstance(exc, trip_service.NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, trip_service.InvalidStateError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/", response_model=list[TripResponse])
def list_trips(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[TripResponse]:
    query = db.query(Trip).join(TripRequest, Trip.request_id == TripRequest.id)
    if current_user.role != UserRole.DISPATCHER:
        query = query.filter(TripRequest.requester_id == current_user.id)
    trips = query.order_by(Trip.id.desc()).all()
    return [TripResponse.model_validate(t) for t in trips]


@router.get("/{trip_id}", response_model=TripResponse)
def get_trip(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TripResponse:
    trip = _get_trip_or_404(db, trip_id)
    _assert_can_view(trip, current_user)
    return TripResponse.model_validate(trip)


@router.get("/{trip_id}/route", response_model=list[PingResponse])
def get_trip_route(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LocationPing]:
    """
    ONLY the GPS points tagged with this trip's id, in chronological order -
    never the vehicle's broader ping history. This is what the frontend
    draws as the trip's route polyline.
    """
    trip = _get_trip_or_404(db, trip_id)
    _assert_can_view(trip, current_user)
    return (
        db.query(LocationPing)
        .filter(LocationPing.trip_id == trip_id)
        .order_by(LocationPing.timestamp.asc(), LocationPing.id.asc())
        .all()
    )


@router.post(
    "/{trip_id}/start", response_model=TripResponse, dependencies=[Depends(require_dispatcher)]
)
def start_trip(trip_id: int, db: Session = Depends(get_db)) -> TripResponse:
    try:
        trip = trip_service.start_trip(db, trip_id)
    except trip_service.TripServiceError as exc:
        raise _map_service_error(exc)
    return TripResponse.model_validate(trip)


@router.post(
    "/{trip_id}/complete", response_model=TripResponse, dependencies=[Depends(require_dispatcher)]
)
def complete_trip(trip_id: int, db: Session = Depends(get_db)) -> TripResponse:
    try:
        trip = trip_service.complete_trip(db, trip_id)
    except trip_service.TripServiceError as exc:
        raise _map_service_error(exc)
    return TripResponse.model_validate(trip)

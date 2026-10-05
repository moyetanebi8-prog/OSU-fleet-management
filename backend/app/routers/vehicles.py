

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_dispatcher
from app.dependencies.device import require_device_api_key
from app.models.trip import Trip
from app.models.enums import TripStatus
from app.models.location_ping import LocationPing
from app.models.vehicle import Vehicle
from app.schemas.ping import PingResponse
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleResponse,
    VehicleStatusUpdate,
    VehicleUpdate,
)
from app.services.vehicle_service import InvalidStatusTransition, change_vehicle_status

router = APIRouter(
    prefix="/vehicles",
    tags=["vehicles"],
)


def _get_vehicle_or_404(db: Session, vehicle_id: int) -> Vehicle:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found.",
        )
    return vehicle


@router.get(
    "/",
    response_model=list[VehicleResponse],
    dependencies=[Depends(require_dispatcher)],
)
def list_vehicles(db: Session = Depends(get_db)) -> list[Vehicle]:
    return db.query(Vehicle).order_by(Vehicle.id).all()


@router.post(
    "/",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_dispatcher)],
)
def create_vehicle(payload: VehicleCreate, db: Session = Depends(get_db)) -> Vehicle:
    if db.query(Vehicle).filter(Vehicle.plate_number == payload.plate_number).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Plate number '{payload.plate_number}' is already registered.",
        )

    vehicle = Vehicle(
        name=payload.name,
        model=payload.model,
        plate_number=payload.plate_number,
        capacity=payload.capacity,
    )
    db.add(vehicle)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Plate number '{payload.plate_number}' is already registered.",
        )

    db.refresh(vehicle)
    return vehicle


@router.get(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    dependencies=[Depends(require_dispatcher)],
)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)) -> Vehicle:
    return _get_vehicle_or_404(db, vehicle_id)


@router.put(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    dependencies=[Depends(require_dispatcher)],
)
def update_vehicle(
    vehicle_id: int, payload: VehicleUpdate, db: Session = Depends(get_db)
) -> Vehicle:
    vehicle = _get_vehicle_or_404(db, vehicle_id)

    conflict = (
        db.query(Vehicle)
        .filter(
            Vehicle.plate_number == payload.plate_number,
            Vehicle.id != vehicle_id,
        )
        .first()
    )

    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Plate number '{payload.plate_number}' is already registered.",
        )

    vehicle.name = payload.name
    vehicle.model = payload.model
    vehicle.plate_number = payload.plate_number
    vehicle.capacity = payload.capacity

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Plate number '{payload.plate_number}' is already registered.",
        )

    db.refresh(vehicle)
    return vehicle


@router.patch(
    "/{vehicle_id}/status",
    response_model=VehicleResponse,
    dependencies=[Depends(require_dispatcher)],
)
def update_vehicle_status(
    vehicle_id: int, payload: VehicleStatusUpdate, db: Session = Depends(get_db)
) -> Vehicle:
    vehicle = _get_vehicle_or_404(db, vehicle_id)

    try:
        return change_vehicle_status(db, vehicle, payload.status)
    except InvalidStatusTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.delete(
    "/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_dispatcher)],
)
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_db)) -> None:
    vehicle = _get_vehicle_or_404(db, vehicle_id)
    db.delete(vehicle)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a vehicle that has trip or GPS history. "
            "Set it to 'inactive' instead.",
        )


@router.get(
    "/{vehicle_id}/history",
    response_model=list[PingResponse],
    dependencies=[Depends(require_dispatcher)],
)
def get_vehicle_history(
    vehicle_id: int,
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[LocationPing]:
    """
    General GPS history for this vehicle - every ping it has ever sent,
    regardless of whether it was on a trip at the time. For a single
    trip's route only, see GET /trips/{id}/route instead.
    """
    _get_vehicle_or_404(db, vehicle_id)

    return (
        db.query(LocationPing)
        .filter(LocationPing.vehicle_id == vehicle_id)
        .order_by(LocationPing.timestamp.desc(), LocationPing.id.desc())
        .limit(limit)
        .all()
    )


@router.get(
    "/{vehicle_id}/active-trip",
    dependencies=[Depends(require_device_api_key)],
)
def get_vehicle_active_trip(
    vehicle_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """
    Return the current trip route assigned to this vehicle.

    The simulator uses this endpoint to know where the vehicle
    should start and where it should travel.
    """
    _get_vehicle_or_404(db, vehicle_id)

    trip = (
        db.query(Trip)
        .filter(
            Trip.vehicle_id == vehicle_id,
            Trip.status.in_(
                [TripStatus.APPROVED, TripStatus.IN_PROGRESS]
            ),
        )
        .order_by(Trip.id.desc())
        .first()
    )

    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active trip found for this vehicle.",
        )

    request = trip.request

    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip request not found.",
        )

    return {
        "trip_id": trip.id,
        "vehicle_id": vehicle_id,
        "source": request.source,
        "source_lat": request.source_lat,
        "source_lng": request.source_lng,
        "destination": request.destination,
        "destination_lat": request.destination_lat,
        "destination_lng": request.destination_lng,
        "trip_status": trip.status.value,
    }
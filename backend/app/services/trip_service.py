"""
The dispatcher approval workflow (spec sections 10-12).

Design choice worth calling out: vehicle/driver "availability" for a given
time window is computed from TWO independent signals, not one:

1. `status == available` - the resource isn't in maintenance, inactive, or
   already tied to some other trip.
2. No schedule conflict - no existing Trip in `approved` or `in_progress`
   status for that same resource whose planned window overlaps the
   requested window.

In the normal flow, #1 already implies #2 (a resource with an active trip
has status `assigned`/`in_progress`, not `available`) - so signal #2 mostly
exists as a defensive, DB-enforced guard against races: two dispatchers
approving different requests for the same vehicle at nearly the same
moment. `approve_trip_request` re-checks both, inside a transaction, with
row-level locks (`with_for_update`) on the vehicle/driver rows, so the
second concurrent approval fails cleanly instead of silently
double-booking a vehicle.
"""

from datetime import datetime, timezone
import logging

from sqlalchemy.orm import Session

from app.models.driver import Driver
from app.models.enums import DriverStatus, TripRequestStatus, TripStatus, UserRole, VehicleStatus
from app.models.location_ping import LocationPing
from app.models.trip import Trip
from app.models.trip_request import TripRequest
from app.models.trip_request_traveler import TripRequestTraveler
from app.models.user import User
from app.models.vehicle import Vehicle
from app.services import distance_service, notification_service

logger = logging.getLogger(__name__)

ACTIVE_TRIP_STATUSES = (TripStatus.APPROVED, TripStatus.IN_PROGRESS)


class TripServiceError(Exception):
    """Base class for all business-rule errors raised by this module."""


class NotFoundError(TripServiceError):
    """The trip request / vehicle / driver referenced doesn't exist -> 404."""


class InvalidStateError(TripServiceError):
    """The operation doesn't make sense given current state (e.g.
    approving an already-approved request) -> 400."""


class ConflictError(TripServiceError):
    """The requested assignment can't be satisfied right now (unavailable
    resource, insufficient capacity, schedule clash) -> 409."""


def _vehicle_has_conflict(
    db: Session, vehicle_id: int, start: datetime, end: datetime, exclude_trip_id: int | None = None
) -> bool:
    query = db.query(Trip.id).filter(
        Trip.vehicle_id == vehicle_id,
        Trip.status.in_(ACTIVE_TRIP_STATUSES),
        Trip.planned_start_time < end,
        Trip.planned_end_time > start,
    )
    if exclude_trip_id is not None:
        query = query.filter(Trip.id != exclude_trip_id)
    return db.query(query.exists()).scalar()


def _driver_has_conflict(
    db: Session, driver_id: int, start: datetime, end: datetime, exclude_trip_id: int | None = None
) -> bool:
    query = db.query(Trip.id).filter(
        Trip.driver_id == driver_id,
        Trip.status.in_(ACTIVE_TRIP_STATUSES),
        Trip.planned_start_time < end,
        Trip.planned_end_time > start,
    )
    if exclude_trip_id is not None:
        query = query.filter(Trip.id != exclude_trip_id)
    return db.query(query.exists()).scalar()


def get_trip_request_locked(db: Session, request_id: int) -> TripRequest:
    trip_request = (
        db.query(TripRequest).filter(TripRequest.id == request_id).with_for_update().first()
    )
    if trip_request is None:
        raise NotFoundError("Trip request not found.")
    return trip_request


def get_available_vehicles(db: Session, trip_request: TripRequest) -> list[Vehicle]:
    candidates = (
        db.query(Vehicle)
        .filter(
            Vehicle.status == VehicleStatus.AVAILABLE,
            Vehicle.capacity >= trip_request.passenger_count,
        )
        .order_by(Vehicle.id)
        .all()
    )
    return [
        v
        for v in candidates
        if not _vehicle_has_conflict(db, v.id, trip_request.requested_start, trip_request.requested_end)
    ]


def get_available_drivers(db: Session, trip_request: TripRequest) -> list[Driver]:
    candidates = (
        db.query(Driver).filter(Driver.status == DriverStatus.AVAILABLE).order_by(Driver.id).all()
    )
    return [
        d
        for d in candidates
        if not _driver_has_conflict(db, d.id, trip_request.requested_start, trip_request.requested_end)
    ]


def approve_trip_request(db: Session, request_id: int, vehicle_id: int, driver_id: int) -> Trip:
    """
    Runs entirely inside one DB transaction: validate -> create Trip ->
    assign vehicle -> assign driver -> flip request status. Any failure
    raises before `db.commit()`, so nothing partial is ever persisted.
    """
    trip_request = get_trip_request_locked(db, request_id)

    if trip_request.status != TripRequestStatus.PENDING:
        raise InvalidStateError(
            f"Trip request is '{trip_request.status.value}'; only pending requests can be approved."
        )

    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).with_for_update().first()
    if vehicle is None:
        raise NotFoundError("Vehicle not found.")

    driver = db.query(Driver).filter(Driver.id == driver_id).with_for_update().first()
    if driver is None:
        raise NotFoundError("Driver not found.")

    if vehicle.status != VehicleStatus.AVAILABLE:
        raise ConflictError(f"Vehicle is not available (current status: '{vehicle.status.value}').")

    if driver.status != DriverStatus.AVAILABLE:
        raise ConflictError(f"Driver is not available (current status: '{driver.status.value}').")

    if vehicle.capacity < trip_request.passenger_count:
        raise ConflictError(
            f"Vehicle capacity ({vehicle.capacity}) is less than the requested "
            f"passenger count ({trip_request.passenger_count})."
        )

    if _vehicle_has_conflict(db, vehicle.id, trip_request.requested_start, trip_request.requested_end):
        raise ConflictError("Vehicle already has a conflicting trip in this time window.")

    if _driver_has_conflict(db, driver.id, trip_request.requested_start, trip_request.requested_end):
        raise ConflictError("Driver already has a conflicting trip in this time window.")

    trip = Trip(
        request_id=trip_request.id,
        vehicle_id=vehicle.id,
        driver_id=driver.id,
        status=TripStatus.APPROVED,
        planned_start_time=trip_request.requested_start,
        planned_end_time=trip_request.requested_end,
    )
    db.add(trip)

    trip_request.status = TripRequestStatus.APPROVED
    vehicle.status = VehicleStatus.ASSIGNED
    driver.status = DriverStatus.ASSIGNED

    db.commit()
    db.refresh(trip)

    # Best-effort, strictly after commit: a notification problem must never
    # roll back or block an approval that has already succeeded (feature
    # spec section 9). notification_service catches its own per-recipient
    # failures; this outer guard is a second layer in case something in
    # there raises anyway (e.g. a DB hiccup while writing the log rows).
    try:
        notification_service.notify_trip_approved(db, trip, trip_request)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "notify_trip_approved failed for trip #%s (approval unaffected): %s", trip.id, exc
        )

    return trip


def decline_trip_request(db: Session, request_id: int, reason: str) -> TripRequest:
    trip_request = get_trip_request_locked(db, request_id)

    if trip_request.status != TripRequestStatus.PENDING:
        raise InvalidStateError(
            f"Trip request is '{trip_request.status.value}'; only pending requests can be declined."
        )

    if not reason or not reason.strip():
        raise InvalidStateError("A non-empty decline reason is required.")

    trip_request.status = TripRequestStatus.DECLINED
    trip_request.decline_reason = reason.strip()

    db.commit()
    db.refresh(trip_request)

    # Best-effort notification after rejection has already committed.
    # A notification/email failure must never undo or block the rejection.
    try:
        notification_service.notify_trip_rejected(
            db,
            trip_request,
            trip_request.decline_reason,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "notify_trip_rejected failed for trip request #%s "
            "(rejection unaffected): %s",
            trip_request.id,
            exc,
        )

    return trip_request

def get_trip_locked(db: Session, trip_id: int) -> Trip:
    trip = db.query(Trip).filter(Trip.id == trip_id).with_for_update().first()
    if trip is None:
        raise NotFoundError("Trip not found.")
    return trip


def start_trip(db: Session, trip_id: int) -> Trip:
    """
    Only an Approved trip can start (spec section 14). The start position is
    NOT fabricated and NOT pulled from arbitrary vehicle history - it's the
    vehicle's most recent LocationPing at the moment of starting. That
    specific ping is then tagged with this trip's id, marking it as the
    first point of the trip's own route (the rest of the route accumulates
    via the GPS ingestion pipeline in Phase 8/9, which attaches every
    subsequent ping for this vehicle to this trip while it stays
    `in_progress`).
    """
    trip = get_trip_locked(db, trip_id)

    if trip.status != TripStatus.APPROVED:
        raise InvalidStateError(
            f"Trip is '{trip.status.value}'; only approved trips can be started."
        )

    latest_ping = (
        db.query(LocationPing)
        .filter(LocationPing.vehicle_id == trip.vehicle_id)
        # id as a tiebreaker: timestamps can tie (identical GPS ping
        # bursts, or - as in the test suite - multiple inserts within the
        # same DB transaction where func.now() is fixed for the whole
        # transaction), so ordering by timestamp alone isn't deterministic.
        .order_by(LocationPing.timestamp.desc(), LocationPing.id.desc())
        .first()
    )
    if latest_ping is None:
        raise ConflictError(
            "No GPS location has been reported for this vehicle yet; "
            "it must send at least one location ping before its trip can start."
        )

    vehicle = db.query(Vehicle).filter(Vehicle.id == trip.vehicle_id).with_for_update().first()
    driver = db.query(Driver).filter(Driver.id == trip.driver_id).with_for_update().first()

    trip.status = TripStatus.IN_PROGRESS
    trip.actual_start_time = datetime.now(timezone.utc)
    trip.start_lat = latest_ping.lat
    trip.start_lng = latest_ping.lng
    latest_ping.trip_id = trip.id

    vehicle.status = VehicleStatus.IN_PROGRESS
    driver.status = DriverStatus.DRIVING

    db.commit()
    db.refresh(trip)
    return trip


def complete_trip(db: Session, trip_id: int) -> Trip:
    """
    Only an In Progress trip can complete (spec section 18). Distance is
    calculated ONLY from LocationPing rows tagged with this trip's id -
    never the vehicle's full ping history - via distance_service, which
    sums consecutive-point distances along the actual route rather than a
    straight line between the first and last point.
    """
    trip = get_trip_locked(db, trip_id)

    if trip.status != TripStatus.IN_PROGRESS:
        raise InvalidStateError(
            f"Trip is '{trip.status.value}'; only in-progress trips can be completed."
        )

    trip_points = (
        db.query(LocationPing)
        .filter(LocationPing.trip_id == trip.id)
        .order_by(LocationPing.timestamp.asc(), LocationPing.id.asc())
        .all()
    )
    if not trip_points:
        raise ConflictError(
            "No GPS points have been recorded for this trip; it cannot be completed "
            "without at least a starting position."
        )

    last_point = trip_points[-1]
    vehicle = db.query(Vehicle).filter(Vehicle.id == trip.vehicle_id).with_for_update().first()
    driver = db.query(Driver).filter(Driver.id == trip.driver_id).with_for_update().first()

    trip.status = TripStatus.COMPLETED
    trip.actual_end_time = datetime.now(timezone.utc)
    trip.end_lat = last_point.lat
    trip.end_lng = last_point.lng
    trip.distance_km = distance_service.calculate_route_distance_km(
        [(p.lat, p.lng) for p in trip_points]
    )

    vehicle.status = VehicleStatus.AVAILABLE
    driver.status = DriverStatus.AVAILABLE

    db.commit()
    db.refresh(trip)
    return trip


def create_trip_request_with_travelers(
    db: Session,
    requester: User,
    *,
    purpose: str,
    source: str,
    source_lat: float | None,
    source_lng: float | None,
    destination: str,
    destination_lat: float | None,
    destination_lng: float | None,
    requested_start: datetime,
    requested_end: datetime,
    traveler_ids: list[int],
) -> TripRequest:
    """
    Creates a TripRequest and its traveler rows in one transaction.

    The source and destination are supplied by the requester.
    Their coordinates are supplied by the geocoding service.
    No route or location is hard-coded.
    """

    unique_traveler_ids = set(traveler_ids)
    unique_traveler_ids.add(requester.id)

    travelers = (
        db.query(User)
        .filter(User.id.in_(unique_traveler_ids))
        .all()
    )

    found_ids = {u.id for u in travelers}
    missing_ids = unique_traveler_ids - found_ids

    if missing_ids:
        raise NotFoundError(
            f"Traveler id(s) not found: {sorted(missing_ids)}."
        )

    for traveler in travelers:
        if traveler.id == requester.id:
            continue

        if not traveler.is_active:
            raise InvalidStateError(
                f"'{traveler.username}' is not an active account "
                "and cannot be selected."
            )

        if traveler.role != UserRole.REQUESTER:
            raise InvalidStateError(
                f"'{traveler.username}' is a dispatcher account, "
                "not an employee, and cannot be selected as a traveler."
            )

    trip_request = TripRequest(
    requester_id=requester.id,
    purpose=purpose,
    source=source,
    source_lat=source_lat,
    source_lng=source_lng,
    destination=destination,
    destination_lat=destination_lat,
    destination_lng=destination_lng,
    requested_start=requested_start,
    requested_end=requested_end,
    status=TripRequestStatus.PENDING,
)
    db.add(trip_request)
    db.flush()

    for traveler_id in unique_traveler_ids:
        db.add(
            TripRequestTraveler(
                trip_request_id=trip_request.id,
                user_id=traveler_id,
            )
        )
    db.commit()
    db.refresh(trip_request)

    return trip_request

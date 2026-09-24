"""
Vehicle business logic.

Status is never a free-form field a client can set to anything (spec
section 7: "do not allow arbitrary invalid statuses"). Beyond the DB-level
enum CHECK constraint, this module enforces WHICH transitions are valid:

- `assigned` and `in_progress` are set only by the trip workflow
  (trip_service, Phase 6/7) when a trip is approved/started - never by a
  direct dispatcher edit.
- A dispatcher can manually toggle a vehicle between `available`,
  `maintenance`, and `inactive` - but only while it isn't currently tied to
  an active trip.
"""

from sqlalchemy.orm import Session

from app.models.enums import VehicleStatus
from app.models.vehicle import Vehicle

MANUALLY_SETTABLE_STATUSES = {
    VehicleStatus.AVAILABLE,
    VehicleStatus.MAINTENANCE,
    VehicleStatus.INACTIVE,
}


class InvalidStatusTransition(ValueError):
    pass


def change_vehicle_status(db: Session, vehicle: Vehicle, new_status: VehicleStatus) -> Vehicle:
    if vehicle.status not in MANUALLY_SETTABLE_STATUSES:
        raise InvalidStatusTransition(
            f"Vehicle is currently '{vehicle.status.value}' and tied to an active trip; "
            "its status cannot be changed manually until that trip is completed or cancelled."
        )
    if new_status not in MANUALLY_SETTABLE_STATUSES:
        raise InvalidStatusTransition(
            f"'{new_status.value}' is set automatically by the trip workflow and cannot be "
            "assigned manually."
        )

    vehicle.status = new_status
    db.commit()
    db.refresh(vehicle)
    return vehicle

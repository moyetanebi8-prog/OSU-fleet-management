"""Driver business logic - mirrors vehicle_service's status-transition rules."""

from sqlalchemy.orm import Session

from app.models.driver import Driver
from app.models.enums import DriverStatus

MANUALLY_SETTABLE_STATUSES = {DriverStatus.AVAILABLE, DriverStatus.INACTIVE}


class InvalidStatusTransition(ValueError):
    pass


def change_driver_status(db: Session, driver: Driver, new_status: DriverStatus) -> Driver:
    if driver.status not in MANUALLY_SETTABLE_STATUSES:
        raise InvalidStatusTransition(
            f"Driver is currently '{driver.status.value}' and tied to an active trip; "
            "their status cannot be changed manually until that trip is completed or cancelled."
        )
    if new_status not in MANUALLY_SETTABLE_STATUSES:
        raise InvalidStatusTransition(
            f"'{new_status.value}' is set automatically by the trip workflow and cannot be "
            "assigned manually."
        )

    driver.status = new_status
    db.commit()
    db.refresh(driver)
    return driver

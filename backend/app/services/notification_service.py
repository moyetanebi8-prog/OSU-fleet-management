"""
Notification creation + real email sending for trip approval.

Called as a best-effort step AFTER a trip approval has already committed
(see trip_service.approve_trip_request), so a notification failure can
never roll back or block the approval itself (feature spec's explicit
requirement). Each recipient's send is independent - one failing (bad
address, mail server down) never stops the others.

Every recipient - requester, traveler, or driver - gets a real
Notification row via `_create_and_send`, which calls the real
email_service.send_email. If SMTP isn't configured (see
email_service.EmailNotConfiguredError) or the send fails for any other
reason, the row is marked `failed` with the real error message - never
silently marked `sent` when nothing actually went out.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.driver import Driver
from app.models.enums import NotificationStatus, NotificationType
from app.models.notification import Notification
from app.models.trip import Trip
from app.models.trip_request import TripRequest
from app.models.trip_request_traveler import TripRequestTraveler
from app.models.user import User
from app.models.vehicle import Vehicle
from app.services import email_service

logger = logging.getLogger(__name__)


def _build_message(
    trip: Trip, trip_request: TripRequest, vehicle: Vehicle, driver: Driver, travelers: list[User]
) -> str:
    traveler_lines = "\n".join(f"  - {t.full_name}" for t in travelers)
    return (
        f"Trip #{trip.id}\n\n"
        f"Requester: {trip_request.requester.full_name}\n\n"
        f"Travelers:\n{traveler_lines}\n\n"
        f"Destination: {trip_request.destination}\n"
        f"Purpose: {trip_request.purpose}\n\n"
        f"Departure: {trip.planned_start_time.isoformat()}\n"
        f"Return: {trip.planned_end_time.isoformat()}\n\n"
        f"Vehicle: {vehicle.name} ({vehicle.plate_number})\n"
        f"Driver: {driver.name}"
    )


def _create_and_send(
    db: Session,
    *,
    recipient_email: str,
    recipient_user_id: int | None,
    recipient_driver_id: int | None,
    notification_type: NotificationType,
    subject: str,
    message: str,
    trip_request_id: int,
    trip_id: int,
) -> Notification:
    notification = Notification(
        recipient_user_id=recipient_user_id,
        recipient_driver_id=recipient_driver_id,
        recipient_email=recipient_email,
        trip_request_id=trip_request_id,
        trip_id=trip_id,
        type=notification_type,
        subject=subject,
        message=message,
        status=NotificationStatus.PENDING,
    )
    db.add(notification)
    db.flush()

    try:
        email_service.send_email(to_email=recipient_email, subject=subject, body=message)
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now(timezone.utc)
    except Exception as exc:  # noqa: BLE001 - a failed send must never propagate
        notification.status = NotificationStatus.FAILED
        notification.error_message = str(exc)[:2000]
        logger.warning("Notification %s to %s failed: %s", notification.id, recipient_email, exc)

    return notification


def notify_trip_approved(db: Session, trip: Trip, trip_request: TripRequest) -> list[Notification]:
    """
    Notifies the requester, every traveler, and the assigned driver by
    real email that a trip has been approved. Skips (and logs) any
    recipient with no email on file rather than crashing - an admin who
    imported employees without emails, or an older Driver row from before
    the email column existed, shouldn't take down the whole notification
    batch.
    """
    vehicle = db.get(Vehicle, trip.vehicle_id)
    driver = db.get(Driver, trip.driver_id)

    traveler_users = (
        db.query(User)
        .join(TripRequestTraveler, TripRequestTraveler.user_id == User.id)
        .filter(TripRequestTraveler.trip_request_id == trip_request.id)
        .all()
    )
    message = _build_message(trip, trip_request, vehicle, driver, traveler_users)
    subject = f"Trip #{trip.id} approved - {trip_request.destination}"

    notifications: list[Notification] = []

    for user in traveler_users:
        if not user.email:
            logger.warning("Skipping notification to user %s: no email on file.", user.username)
            continue
        notification_type = (
            NotificationType.TRIP_APPROVED_REQUESTER
            if user.id == trip_request.requester_id
            else NotificationType.TRIP_APPROVED_TRAVELER
        )
        notifications.append(
            _create_and_send(
                db,
                recipient_email=user.email,
                recipient_user_id=user.id,
                recipient_driver_id=None,
                notification_type=notification_type,
                subject=subject,
                message=message,
                trip_request_id=trip_request.id,
                trip_id=trip.id,
            )
        )

    if driver and driver.email:
        notifications.append(
            _create_and_send(
                db,
                recipient_email=driver.email,
                recipient_user_id=None,
                recipient_driver_id=driver.id,
                notification_type=NotificationType.TRIP_APPROVED_DRIVER,
                subject=subject,
                message=message,
                trip_request_id=trip_request.id,
                trip_id=trip.id,
            )
        )
    elif driver:
        logger.warning("Driver %s has no email on file - cannot send assignment notification.", driver.name)

    db.commit()
    for n in notifications:
        db.refresh(n)
    return notifications
def notify_trip_rejected(
    db: Session,
    trip_request: TripRequest,
    reason: str,
) -> Notification | None:
    """
    Notifies the trip requester that their trip request was rejected.

    The rejection reason is included in the notification.
    The notification is best-effort and should never block the
    already-completed rejection.
    """
    requester = db.get(User, trip_request.requester_id)

    if requester is None:
        logger.warning(
            "Cannot notify rejected trip request #%s: requester not found.",
            trip_request.id,
        )
        return None

    if not requester.email:
        logger.warning(
            "Cannot notify rejected trip request #%s: requester %s has no email.",
            trip_request.id,
            requester.username,
        )
        return None

    subject = f"Trip request #{trip_request.id} rejected - {trip_request.destination}"

    message = (
        f"Trip Request #{trip_request.id}\n\n"
        f"Requester: {requester.full_name}\n\n"
        f"Source: {trip_request.source}\n"
        f"Destination: {trip_request.destination}\n"
        f"Purpose: {trip_request.purpose}\n\n"
        f"Departure: {trip_request.requested_start.isoformat()}\n"
        f"Return: {trip_request.requested_end.isoformat()}\n\n"
        f"Status: REJECTED\n\n"
        f"Rejection reason:\n"
        f"{reason}"
    )

    notification = _create_and_send(
        db,
        recipient_email=requester.email,
        recipient_user_id=requester.id,
        recipient_driver_id=None,
        notification_type=NotificationType.TRIP_REJECTED_REQUESTER,
        subject=subject,
        message=message,
        trip_request_id=trip_request.id,
        trip_id=None,
    )

    db.commit()
    db.refresh(notification)

    return notification

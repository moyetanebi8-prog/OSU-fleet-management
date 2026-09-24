from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import NotificationStatus, NotificationType


class Notification(Base):
    """
    A record that someone SHOULD be informed of a trip event (currently:
    approval), and whether that actually happened.

    A recipient is either a User (requester/traveler) OR a Driver - never
    both, never neither. Drivers don't have login accounts in this system,
    so they can't be a `recipient_user_id` - `recipient_driver_id` exists
    specifically so driver notifications get the same tracking/history
    guarantee as everyone else's, not a second-class "just log it and
    hope" path.

    `recipient_email` is stored directly (denormalized) rather than always
    joined from User/Driver - it's the actual address a send was attempted
    against, which matters for audit trail even if the underlying
    account's email later changes.

    This table tracks notification intent and delivery status. Whether it
    sends a REAL email depends on app/services/email_service.py actually
    being configured with real SMTP credentials (see .env) - if it isn't,
    sends fail loudly and are recorded as `failed` here with the real
    error, not silently marked `sent`.
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    recipient_driver_id: Mapped[int | None] = mapped_column(
        ForeignKey("drivers.id"), nullable=True, index=True
    )
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)

    trip_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("trip_requests.id"), nullable=True, index=True
    )
    trip_id: Mapped[int | None] = mapped_column(ForeignKey("trips.id"), nullable=True, index=True)

    type: Mapped[NotificationType] = mapped_column(
        Enum(
            NotificationType, name="notification_type", native_enum=False, length=40,
            create_constraint=True,
        ),
        nullable=False,
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[NotificationStatus] = mapped_column(
        Enum(
            NotificationStatus, name="notification_status", native_enum=False, length=20,
            create_constraint=True,
        ),
        nullable=False,
        default=NotificationStatus.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    recipient_user: Mapped["User | None"] = relationship()
    recipient_driver: Mapped["Driver | None"] = relationship()

    __table_args__ = (
        CheckConstraint(
            "(recipient_user_id IS NOT NULL) != (recipient_driver_id IS NOT NULL)",
            name="ck_notification_exactly_one_recipient",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Notification id={self.id} type={self.type.value} status={self.status.value}>"

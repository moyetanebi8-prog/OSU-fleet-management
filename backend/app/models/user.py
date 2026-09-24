from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import UserRole


class User(Base):
    """
    A system account. Role determines what the account can do:
    - requester: creates/views their own trip requests only
    - dispatcher: reviews/approves/declines requests, manages the fleet
    - admin: manages employee/user accounts (add employees, bulk CSV
      import, activate/deactivate any account) - does not touch trips or
      fleet operations

    IMPORTANT: there is no public self-registration anymore. Employee
    (requester) accounts are created only by an admin, one at a time or
    via CSV import (see app/routers/admin.py). Dispatcher and admin
    accounts are created only via scripts/create_dispatcher.py /
    scripts/create_admin.py or by an existing admin. This is a deliberate
    access-control decision: only pre-provisioned company employees can
    sign in, not anyone who visits the login page.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    # Nullable at the DB level only for backward compatibility with rows
    # created before this column existed - every account created going
    # forward (admin panel, CSV import, seed scripts) requires a real
    # email, since it's now used for account/notification delivery.
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            length=20,
            create_constraint=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=UserRole.REQUESTER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    trip_requests: Mapped[list["TripRequest"]] = relationship(
        back_populates="requester", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"<User id={self.id} username={self.username!r} role={self.role.value}>"

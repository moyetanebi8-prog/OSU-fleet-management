from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserSummary(BaseModel):
    """Minimal, safe-to-expose view of a user account - no password_hash,
    nothing beyond what's needed to identify someone in a list."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    email: str | None = None


class EmployeeCreate(BaseModel):
    """
    Used by an admin to add a single employee (requester account).
    `password` is optional - if omitted, a secure random temporary
    password is generated and returned once in the response (see
    EmployeeCreateResult) so the admin can hand it to the employee
    out-of-band, and it's included in the employee's onboarding email if
    SMTP is configured.
    """

    username: str = Field(min_length=3, max_length=64)
    full_name: str = Field(min_length=1, max_length=128)
    email: EmailStr
    password: str | None = Field(default=None, min_length=8, max_length=128)


class EmployeeCreateResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    email: str | None
    temporary_password: str | None = None
    onboarding_email_sent: bool = False


class CsvImportRowError(BaseModel):
    row_number: int
    data: dict
    error: str


class CsvImportResult(BaseModel):
    created: list[EmployeeCreateResult]
    errors: list[CsvImportRowError]


class UserManagementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    email: str | None
    role: UserRole
    is_active: bool
    created_at: datetime


class UserStatusUpdate(BaseModel):
    is_active: bool


class DispatcherOrAdminCreate(BaseModel):
    """Used by an existing admin to create additional dispatcher or admin
    accounts through the panel, complementing (not replacing) the CLI
    bootstrap scripts needed to create the very first admin account."""

    username: str = Field(min_length=3, max_length=64)
    full_name: str = Field(min_length=1, max_length=128)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole

    def validate_role(self) -> None:
        if self.role not in (UserRole.DISPATCHER, UserRole.ADMIN):
            raise ValueError("role must be 'dispatcher' or 'admin'.")

"""
Employee account creation, one at a time or via CSV import.

This is now the ONLY way requester accounts get created - there is no
public self-registration anymore (see app/routers/auth.py). An admin adds
employees here, individually or by uploading a CSV, and each one gets a
real account plus (if SMTP is configured) a welcome email with their
credentials.
"""

import csv
import io
import logging
import secrets

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import CsvImportResult, CsvImportRowError, EmployeeCreateResult
from app.services import email_service
from app.services.auth import hash_password

logger = logging.getLogger(__name__)

REQUIRED_CSV_COLUMNS = {"username", "full_name", "email"}


class DuplicateEmployeeError(ValueError):
    """Username or email already exists - maps to 409 in the router."""


def generate_temporary_password() -> str:
    # url-safe, ~16 chars, plenty of entropy for a one-time temp password
    # the employee is expected to change after first login.
    return secrets.token_urlsafe(12)


def _send_onboarding_email(user: User, temporary_password: str) -> bool:
    subject = "Your Fleet Management System account"
    body = (
        f"Hi {user.full_name},\n\n"
        f"An account has been created for you on the Fleet Management System.\n\n"
        f"Username: {user.username}\n"
        f"Temporary password: {temporary_password}\n\n"
        f"Please log in and change your password as soon as possible."
    )
    try:
        email_service.send_email(to_email=user.email, subject=subject, body=body)
        return True
    except Exception as exc:  # noqa: BLE001 - onboarding email failure must not block account creation
        logger.warning("Onboarding email to %s failed: %s", user.email, exc)
        return False


def create_employee(
    db: Session, *, username: str, full_name: str, email: str, password: str | None
) -> EmployeeCreateResult:
    if db.query(User).filter(User.username == username).first():
        raise DuplicateEmployeeError(f"Username '{username}' is already taken.")
    if db.query(User).filter(User.email == email).first():
        raise DuplicateEmployeeError(f"Email '{email}' is already registered.")

    temporary_password = password if password else generate_temporary_password()
    was_generated = password is None

    user = User(
        username=username,
        full_name=full_name,
        email=email,
        password_hash=hash_password(temporary_password),
        role=UserRole.REQUESTER,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateEmployeeError(
            f"Username '{username}' or email '{email}' is already in use."
        )
    db.refresh(user)

    onboarding_sent = _send_onboarding_email(user, temporary_password)

    return EmployeeCreateResult(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        # Only ever return the password when we generated it - if the
        # admin supplied their own, we never echo it back.
        temporary_password=temporary_password if was_generated else None,
        onboarding_email_sent=onboarding_sent,
    )


def import_employees_from_csv(db: Session, file_content: bytes) -> CsvImportResult:
    """
    Expects a CSV with at least `username,full_name,email` columns (a
    `password` column is optional per-row - omit it to auto-generate one).
    Each row is created independently: one bad row (duplicate username,
    missing field) is recorded as an error and processing continues with
    the rest, rather than the whole file failing on one bad line.
    """
    text = file_content.decode("utf-8-sig")  # handles a leading BOM from Excel exports gracefully
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None or not REQUIRED_CSV_COLUMNS.issubset(set(reader.fieldnames)):
        raise ValueError(
            f"CSV must have at least these columns: {', '.join(sorted(REQUIRED_CSV_COLUMNS))}. "
            f"Found: {reader.fieldnames}"
        )

    created: list[EmployeeCreateResult] = []
    errors: list[CsvImportRowError] = []

    for row_number, row in enumerate(reader, start=2):  # row 1 is the header
        try:
            username = (row.get("username") or "").strip()
            full_name = (row.get("full_name") or "").strip()
            email = (row.get("email") or "").strip()
            password = (row.get("password") or "").strip() or None

            if not username or not full_name or not email:
                raise ValueError("username, full_name, and email are all required.")

            result = create_employee(
                db, username=username, full_name=full_name, email=email, password=password
            )
            created.append(result)
        except DuplicateEmployeeError as exc:
            errors.append(CsvImportRowError(row_number=row_number, data=row, error=str(exc)))
        except ValueError as exc:
            errors.append(CsvImportRowError(row_number=row_number, data=row, error=str(exc)))

    return CsvImportResult(created=created, errors=errors)

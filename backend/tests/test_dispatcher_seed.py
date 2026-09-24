import pytest

from app.models.enums import UserRole
from app.models.user import User
from app.services.auth import verify_password
from scripts.create_admin import create_admin_with_session
from scripts.create_dispatcher import create_dispatcher_with_session


def test_create_dispatcher_creates_dispatcher_role(db_session):
    user = create_dispatcher_with_session(db_session, "ops1", "Ops One", "dispatcherpass1")
    assert user.role == UserRole.DISPATCHER
    assert user.is_active is True


def test_create_dispatcher_password_is_hashed(db_session):
    user = create_dispatcher_with_session(db_session, "ops2", "Ops Two", "dispatcherpass1")
    assert user.password_hash != "dispatcherpass1"
    assert verify_password("dispatcherpass1", user.password_hash)


def test_create_dispatcher_rejects_duplicate_username(db_session):
    create_dispatcher_with_session(db_session, "ops3", "Ops Three", "dispatcherpass1")
    with pytest.raises(ValueError):
        create_dispatcher_with_session(db_session, "ops3", "Ops Three Again", "anotherpass1")


def test_admin_created_employee_is_always_a_requester(client, admin_headers, db_session):
    """Employees are always created as requester accounts through the
    admin panel, regardless of what's sent - EmployeeCreate has no `role`
    field at all, so there's no way to request anything else."""
    response = client.post(
        "/api/v1/admin/employees/",
        json={
            "username": "sneaky",
            "full_name": "Sneaky",
            "email": "sneaky@example.com",
            "role": "dispatcher",  # not a real field on EmployeeCreate - silently ignored
        },
        headers=admin_headers,
    )
    assert response.status_code == 201

    created = db_session.query(User).filter(User.username == "sneaky").first()
    assert created is not None
    assert created.role == UserRole.REQUESTER


def test_create_admin_creates_admin_role(db_session):
    user = create_admin_with_session(db_session, "boss1", "Boss One", "adminpass123")
    assert user.role == UserRole.ADMIN
    assert user.is_active is True


def test_create_admin_password_is_hashed(db_session):
    user = create_admin_with_session(db_session, "boss2", "Boss Two", "adminpass123")
    assert user.password_hash != "adminpass123"
    assert verify_password("adminpass123", user.password_hash)


def test_create_admin_rejects_duplicate_username(db_session):
    create_admin_with_session(db_session, "boss3", "Boss Three", "adminpass123")
    with pytest.raises(ValueError):
        create_admin_with_session(db_session, "boss3", "Boss Three Again", "anotherpass1")

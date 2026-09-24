import pytest
from fastapi import HTTPException

from app.dependencies.auth import require_dispatcher, require_requester
from app.models.enums import UserRole
from app.models.user import User


def _user(role: UserRole) -> User:
    return User(
        id=1,
        username="test",
        full_name="Test User",
        password_hash="irrelevant",
        role=role,
        is_active=True,
    )


def test_require_dispatcher_allows_dispatcher():
    dispatcher = _user(UserRole.DISPATCHER)
    assert require_dispatcher(dispatcher) is dispatcher


def test_require_dispatcher_rejects_requester():
    requester = _user(UserRole.REQUESTER)
    with pytest.raises(HTTPException) as exc_info:
        require_dispatcher(requester)
    assert exc_info.value.status_code == 403


def test_require_requester_allows_requester():
    requester = _user(UserRole.REQUESTER)
    assert require_requester(requester) is requester


def test_require_requester_rejects_dispatcher():
    dispatcher = _user(UserRole.DISPATCHER)
    with pytest.raises(HTTPException) as exc_info:
        require_requester(dispatcher)
    assert exc_info.value.status_code == 403

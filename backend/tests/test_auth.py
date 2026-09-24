from app.models.enums import UserRole
from app.models.user import User
from app.services.auth import hash_password

# Registration/employee-creation behavior moved to test_admin.py, since
# there is no public /auth/register anymore - only an admin can create
# accounts. This file covers login/me only.


def test_login_success_returns_bearer_token(client, requester_headers, db_session):
    """requester_headers already logs in during setup - re-login here to
    test the endpoint directly and confirm token shape."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "requester1", "password": "requesterpass1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


def test_login_wrong_password_returns_401(client, requester_headers):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "requester1", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user_returns_401(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "nobody", "password": "whatever123"},
    )
    assert response.status_code == 401


def test_login_rejects_inactive_user(client, db_session):
    user = User(
        username="ghost",
        full_name="Ghost",
        email="ghost@example.com",
        password_hash=hash_password("supersecret1"),
        role=UserRole.REQUESTER,
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "ghost", "password": "supersecret1"},
    )
    assert response.status_code == 401


def test_me_requires_authentication(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user(client, requester_headers):
    response = client.get("/api/v1/auth/me", headers=requester_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "requester1"
    assert body["email"] == "requester1@example.com"


def test_me_rejects_garbage_token(client):
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_me_rejects_expired_token(client):
    """A syntactically valid, correctly-signed token that has simply
    expired must be rejected exactly like an invalid one - jose validates
    the `exp` claim before this ever reaches a DB lookup."""
    from app.services.auth import create_access_token

    expired_token = create_access_token(subject="someone", role="requester", expires_minutes=-1)
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401


def test_register_endpoint_no_longer_exists(client):
    """Regression guard: public self-registration was deliberately
    removed. If this ever starts returning something other than 404/405,
    that's a regression in the access-control model, not a feature."""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "anyone", "full_name": "Anyone", "password": "whatever123"},
    )
    assert response.status_code in (404, 405)

"""
Test database strategy:

- Uses TEST_DATABASE_URL (a separate database from development/production,
  see db-init/01-create-test-db.sql), never the real fms_db.
- Schema is created once per test session via Base.metadata.create_all.
- Each individual test runs inside a DB transaction that is rolled back
  afterwards, so tests never leak state into one another and never need to
  manually clean up rows. Route code calls session.commit() as normal
  (e.g. app/routers/auth.py) - that only releases a SAVEPOINT here, thanks
  to the after_transaction_end listener below, which is the standard
  SQLAlchemy recipe for nesting app-level commits inside a rolled-back
  outer test transaction.
- The FastAPI `get_db` dependency is overridden to hand out that same
  transactional session, so the API layer and the test's own assertions
  see identical data.

ACCOUNT CREATION IN TESTS: there is no public self-registration in this
system anymore - employee (requester) accounts are created by an admin.
`admin_headers` creates the admin account tests need for that; `client`
fixture handles the rest. `requester_headers` and `make_employee_headers`
both go through the real admin-employee-creation endpoint, exactly the way
production works - not a test-only shortcut.
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401 - ensures all tables are registered
from app.database import Base, get_db
from app.main import app
from scripts.create_admin import create_admin_with_session
from scripts.create_dispatcher import create_dispatcher_with_session

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://fms_user:fms_password@localhost:5432/fms_test_db",
)

engine = create_engine(TEST_DATABASE_URL, future=True)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Start a SAVEPOINT and transparently restart it every time the app
    # code (or a test) calls session.commit(). Without this, an app-level
    # commit would commit the outer transaction too, and the final
    # rollback() below would have nothing left to undo.
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def dispatcher_headers(client, db_session):
    """A real dispatcher account (created directly via the seed-script
    function, exactly the way it happens in production) logged in through
    the real /auth/login endpoint."""
    create_dispatcher_with_session(
        db_session, "dispatcher1", "Dispatcher One", "dispatcherpass1", "dispatcher1@example.com"
    )
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "dispatcher1", "password": "dispatcherpass1"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_headers(client, db_session):
    """A real admin account, the same way the very first admin is created
    in production (scripts/create_admin.py) - not a test-only shortcut."""
    create_admin_with_session(
        db_session, "admin1", "Admin One", "adminpass123", "admin1@example.com"
    )
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "admin1", "password": "adminpass123"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def requester_headers(client, admin_headers):
    """A real requester (employee) account, created the only way it can be
    in this system: by an admin, via POST /admin/employees/ - proving
    requester accounts can never reach dispatcher/admin-only routes
    regardless of how they were created."""
    client.post(
        "/api/v1/admin/employees/",
        json={
            "username": "requester1",
            "full_name": "Requester One",
            "email": "requester1@example.com",
            "password": "requesterpass1",
        },
        headers=admin_headers,
    )
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "requester1", "password": "requesterpass1"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def make_employee_headers(client, admin_headers):
    """
    Factory fixture: call with a username to create an ADDITIONAL employee
    account beyond the shared `requester1` from `requester_headers` -
    used by tests that need two or more distinct requesters (e.g.
    ownership-isolation tests). Replaces the old pattern of each test file
    hand-rolling its own "_register_and_login" helper against the public
    register endpoint, which no longer exists.
    """

    def _make(username: str, password: str = "requesterpass1") -> dict:
        client.post(
            "/api/v1/admin/employees/",
            json={
                "username": username,
                "full_name": username.replace("_", " ").title(),
                "email": f"{username}@example.com",
                "password": password,
            },
            headers=admin_headers,
        )
        login = client.post("/api/v1/auth/login", data={"username": username, "password": password})
        token = login.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture(autouse=True)
def _stub_email_sending(monkeypatch):
    """
    app/services/email_service.py sends REAL email via SMTP - this test
    environment has no mail server configured (nor should it need one to
    verify business logic). By default, every test gets a fake
    `send_email` that always succeeds and records what it was asked to
    send, so notification/onboarding-email tests can verify WHO got
    emailed and WHAT was in it without depending on a real SMTP server.

    tests/test_email_service.py specifically tests the REAL send_email
    function's behavior (including that it correctly raises when
    unconfigured) and overrides this fixture by defining its own
    `_stub_email_sending` with the same name - see that file's comment.
    """
    sent_emails: list[dict] = []

    def _fake_send_email(*, to_email, subject, body):
        sent_emails.append({"to_email": to_email, "subject": subject, "body": body})

    monkeypatch.setattr("app.services.email_service.send_email", _fake_send_email)
    return sent_emails

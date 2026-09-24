import io

from app.models.user import User


# --- access control ---


def test_create_employee_requires_admin(client, requester_headers):
    response = client.post(
        "/api/v1/admin/employees/",
        json={"username": "x", "full_name": "X", "email": "x@example.com"},
        headers=requester_headers,
    )
    assert response.status_code == 403


def test_create_employee_requires_authentication(client):
    response = client.post(
        "/api/v1/admin/employees/",
        json={"username": "x", "full_name": "X", "email": "x@example.com"},
    )
    assert response.status_code == 401


def test_dispatcher_cannot_access_admin_endpoints(client, dispatcher_headers):
    response = client.get("/api/v1/admin/users/", headers=dispatcher_headers)
    assert response.status_code == 403


# --- single employee creation ---


def test_create_employee_success(client, admin_headers):
    response = client.post(
        "/api/v1/admin/employees/",
        json={"username": "alice", "full_name": "Alice Employee", "email": "alice@example.com"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"
    # No password was supplied, so one was generated and returned exactly once.
    assert body["temporary_password"] is not None
    assert len(body["temporary_password"]) >= 8


def test_create_employee_with_explicit_password_does_not_echo_it_back(client, admin_headers):
    response = client.post(
        "/api/v1/admin/employees/",
        json={
            "username": "bob",
            "full_name": "Bob Employee",
            "email": "bob@example.com",
            "password": "explicitpass123",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json()["temporary_password"] is None


def test_created_employee_is_a_requester_and_can_log_in(client, admin_headers):
    create = client.post(
        "/api/v1/admin/employees/",
        json={
            "username": "carol",
            "full_name": "Carol Employee",
            "email": "carol@example.com",
            "password": "explicitpass123",
        },
        headers=admin_headers,
    )
    assert create.status_code == 201

    login = client.post(
        "/api/v1/auth/login", data={"username": "carol", "password": "explicitpass123"}
    )
    assert login.status_code == 200

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert me.json()["role"] == "requester"


def test_create_employee_duplicate_username_returns_409(client, admin_headers):
    payload = {"username": "dave", "full_name": "Dave", "email": "dave@example.com"}
    first = client.post("/api/v1/admin/employees/", json=payload, headers=admin_headers)
    assert first.status_code == 201

    second = client.post(
        "/api/v1/admin/employees/",
        json={"username": "dave", "full_name": "Dave Two", "email": "different@example.com"},
        headers=admin_headers,
    )
    assert second.status_code == 409


def test_create_employee_duplicate_email_returns_409(client, admin_headers):
    client.post(
        "/api/v1/admin/employees/",
        json={"username": "erin1", "full_name": "Erin", "email": "shared@example.com"},
        headers=admin_headers,
    )
    response = client.post(
        "/api/v1/admin/employees/",
        json={"username": "erin2", "full_name": "Erin Two", "email": "shared@example.com"},
        headers=admin_headers,
    )
    assert response.status_code == 409


def test_create_employee_rejects_invalid_email(client, admin_headers):
    response = client.post(
        "/api/v1/admin/employees/",
        json={"username": "frank", "full_name": "Frank", "email": "not-an-email"},
        headers=admin_headers,
    )
    assert response.status_code == 422


# --- CSV import ---


def test_csv_import_creates_multiple_employees(client, admin_headers):
    csv_content = (
        "username,full_name,email\n"
        "csvuser1,CSV User One,csvuser1@example.com\n"
        "csvuser2,CSV User Two,csvuser2@example.com\n"
    )
    response = client.post(
        "/api/v1/admin/employees/import-csv",
        files={"file": ("employees.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["created"]) == 2
    assert body["errors"] == []
    usernames = {c["username"] for c in body["created"]}
    assert usernames == {"csvuser1", "csvuser2"}


def test_csv_import_reports_bad_rows_without_failing_whole_batch(client, admin_headers):
    csv_content = (
        "username,full_name,email\n"
        "goodrow,Good Row,goodrow@example.com\n"
        ",Missing Username,missingun@example.com\n"
    )
    response = client.post(
        "/api/v1/admin/employees/import-csv",
        files={"file": ("employees.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["created"]) == 1
    assert body["created"][0]["username"] == "goodrow"
    assert len(body["errors"]) == 1
    assert body["errors"][0]["row_number"] == 3


def test_csv_import_rejects_missing_required_columns(client, admin_headers):
    csv_content = "name,mail\nsomeone,someone@example.com\n"
    response = client.post(
        "/api/v1/admin/employees/import-csv",
        files={"file": ("employees.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_csv_import_duplicate_username_within_file_reported_as_error(client, admin_headers):
    csv_content = (
        "username,full_name,email\n"
        "dupuser,Dup User,dup1@example.com\n"
        "dupuser,Dup User Again,dup2@example.com\n"
    )
    response = client.post(
        "/api/v1/admin/employees/import-csv",
        files={"file": ("employees.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        headers=admin_headers,
    )
    body = response.json()
    assert len(body["created"]) == 1
    assert len(body["errors"]) == 1


# --- dispatcher/admin account creation via panel ---


def test_admin_can_create_dispatcher_account(client, admin_headers):
    response = client.post(
        "/api/v1/admin/accounts/",
        json={
            "username": "newdispatcher",
            "full_name": "New Dispatcher",
            "email": "newdispatcher@example.com",
            "password": "dispatcherpass1",
            "role": "dispatcher",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json()["role"] == "dispatcher"


def test_admin_cannot_create_requester_via_accounts_endpoint(client, admin_headers):
    """/admin/accounts/ is for dispatcher/admin accounts only - requesters
    go through /admin/employees/ instead, which is where CSV import and
    auto-generated passwords live."""
    response = client.post(
        "/api/v1/admin/accounts/",
        json={
            "username": "sneaky",
            "full_name": "Sneaky",
            "email": "sneaky@example.com",
            "password": "whatever123",
            "role": "requester",
        },
        headers=admin_headers,
    )
    assert response.status_code == 400


# --- user listing/management ---


def test_list_users_requires_admin(client, dispatcher_headers):
    response = client.get("/api/v1/admin/users/", headers=dispatcher_headers)
    assert response.status_code == 403


def test_list_users_returns_all_roles(client, admin_headers, dispatcher_headers, requester_headers):
    response = client.get("/api/v1/admin/users/", headers=admin_headers)
    assert response.status_code == 200
    roles = {u["role"] for u in response.json()}
    assert "admin" in roles
    assert "dispatcher" in roles
    assert "requester" in roles


def test_list_users_filters_by_role(client, admin_headers, requester_headers):
    response = client.get("/api/v1/admin/users/", params={"role": "requester"}, headers=admin_headers)
    assert all(u["role"] == "requester" for u in response.json())


def test_deactivate_user(client, admin_headers, requester_headers, db_session):
    requester = db_session.query(User).filter(User.username == "requester1").first()

    response = client.patch(
        f"/api/v1/admin/users/{requester.id}/status",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    login = client.post(
        "/api/v1/auth/login", data={"username": "requester1", "password": "requesterpass1"}
    )
    assert login.status_code == 401


def test_update_status_nonexistent_user_404(client, admin_headers):
    response = client.patch(
        "/api/v1/admin/users/999999/status", json={"is_active": False}, headers=admin_headers
    )
    assert response.status_code == 404

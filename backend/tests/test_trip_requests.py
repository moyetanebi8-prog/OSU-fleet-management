from datetime import datetime, timedelta, timezone


def _register_and_login(client, admin_headers, username: str) -> dict:
    """Creates an additional employee account via the real admin-employee
    endpoint - there is no public self-registration in this system."""
    client.post(
        "/api/v1/admin/employees/",
        json={
            "username": username,
            "full_name": username.title(),
            "email": f"{username}@example.com",
            "password": "requesterpass1",
        },
        headers=admin_headers,
    )
    login = client.post(
        "/api/v1/auth/login", data={"username": username, "password": "requesterpass1"}
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _future_window(hours_ahead: int = 24, duration_hours: int = 2) -> dict:
    start = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)
    end = start + timedelta(hours=duration_hours)
    return {"requested_start": start.isoformat(), "requested_end": end.isoformat()}


def _base_payload(**overrides) -> dict:
    # No `passenger_count` - that field doesn't exist on TripRequestCreate
    # anymore (see the traveler-selection feature): passenger count is
    # derived server-side from `traveler_ids`, defaulting to just the
    # requester (passenger_count=1) if none are given.
    payload = {
        "purpose": "Client site visit",
        "destination": "Downtown office",
        "traveler_ids": [],
        **_future_window(),
    }
    payload.update(overrides)
    return payload


def test_create_trip_request_requires_authentication(client):
    response = client.post("/api/v1/trip-requests/", json=_base_payload())
    assert response.status_code == 401


def test_create_trip_request_rejects_dispatcher(client, dispatcher_headers):
    response = client.post(
        "/api/v1/trip-requests/", json=_base_payload(), headers=dispatcher_headers
    )
    assert response.status_code == 403


def test_create_trip_request_success(client, requester_headers):
    response = client.post(
        "/api/v1/trip-requests/", json=_base_payload(), headers=requester_headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["requester_username"] == "requester1"
    assert body["decline_reason"] is None
    assert body["trip_id"] is None
    assert body["passenger_count"] == 1  # just the requester, no travelers added


def test_create_trip_request_rejects_end_before_start(client, requester_headers):
    start = datetime.now(timezone.utc) + timedelta(hours=24)
    end = start - timedelta(hours=1)
    response = client.post(
        "/api/v1/trip-requests/",
        json=_base_payload(requested_start=start.isoformat(), requested_end=end.isoformat()),
        headers=requester_headers,
    )
    assert response.status_code == 422


def test_create_trip_request_rejects_invalid_traveler_id(client, requester_headers):
    """The modern equivalent of the old 'invalid passenger_count' test -
    passenger count isn't directly settable anymore, but an invalid
    traveler id is still rejected."""
    response = client.post(
        "/api/v1/trip-requests/",
        json=_base_payload(traveler_ids=[999999]),
        headers=requester_headers,
    )
    assert response.status_code == 404


def test_create_trip_request_ignores_client_supplied_status(client, requester_headers):
    response = client.post(
        "/api/v1/trip-requests/",
        json=_base_payload(status="approved"),
        headers=requester_headers,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending"


def test_requester_only_sees_own_requests(client, admin_headers):
    alice_headers = _register_and_login(client, admin_headers, "alice_req")
    bob_headers = _register_and_login(client, admin_headers, "bob_req")

    client.post("/api/v1/trip-requests/", json=_base_payload(purpose="Alice trip"), headers=alice_headers)
    client.post("/api/v1/trip-requests/", json=_base_payload(purpose="Bob trip"), headers=bob_headers)

    alice_list = client.get("/api/v1/trip-requests/", headers=alice_headers).json()
    purposes = {r["purpose"] for r in alice_list}
    assert "Alice trip" in purposes
    assert "Bob trip" not in purposes


def test_dispatcher_sees_all_requests(client, dispatcher_headers, admin_headers):
    alice_headers = _register_and_login(client, admin_headers, "alice_req2")
    bob_headers = _register_and_login(client, admin_headers, "bob_req2")

    client.post("/api/v1/trip-requests/", json=_base_payload(purpose="Alice trip 2"), headers=alice_headers)
    client.post("/api/v1/trip-requests/", json=_base_payload(purpose="Bob trip 2"), headers=bob_headers)

    all_requests = client.get("/api/v1/trip-requests/", headers=dispatcher_headers).json()
    purposes = {r["purpose"] for r in all_requests}
    assert "Alice trip 2" in purposes
    assert "Bob trip 2" in purposes


def test_list_filters_by_status(client, dispatcher_headers, requester_headers):
    client.post("/api/v1/trip-requests/", json=_base_payload(), headers=requester_headers)

    pending_only = client.get(
        "/api/v1/trip-requests/", params={"status_filter": "pending"}, headers=dispatcher_headers
    ).json()
    assert all(r["status"] == "pending" for r in pending_only)

    declined_only = client.get(
        "/api/v1/trip-requests/", params={"status_filter": "declined"}, headers=dispatcher_headers
    ).json()
    assert declined_only == []


def test_requester_can_view_own_request_by_id(client, requester_headers):
    create = client.post(
        "/api/v1/trip-requests/", json=_base_payload(), headers=requester_headers
    )
    request_id = create.json()["id"]

    response = client.get(f"/api/v1/trip-requests/{request_id}", headers=requester_headers)
    assert response.status_code == 200


def test_requester_cannot_view_others_request(client, admin_headers):
    alice_headers = _register_and_login(client, admin_headers, "alice_req3")
    bob_headers = _register_and_login(client, admin_headers, "bob_req3")

    create = client.post(
        "/api/v1/trip-requests/", json=_base_payload(), headers=alice_headers
    )
    request_id = create.json()["id"]

    response = client.get(f"/api/v1/trip-requests/{request_id}", headers=bob_headers)
    assert response.status_code == 403


def test_dispatcher_can_view_any_request(client, dispatcher_headers, requester_headers):
    create = client.post(
        "/api/v1/trip-requests/", json=_base_payload(), headers=requester_headers
    )
    request_id = create.json()["id"]

    response = client.get(f"/api/v1/trip-requests/{request_id}", headers=dispatcher_headers)
    assert response.status_code == 200


def test_get_nonexistent_request_returns_404(client, dispatcher_headers):
    response = client.get("/api/v1/trip-requests/999999", headers=dispatcher_headers)
    assert response.status_code == 404

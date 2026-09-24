from datetime import datetime, timedelta, timezone

from app.models.enums import NotificationStatus, NotificationType, UserRole
from app.models.notification import Notification
from app.models.user import User
from app.services.auth import hash_password


def _window(hours_ahead: int = 24, duration_hours: int = 2):
    start = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)
    end = start + timedelta(hours=duration_hours)
    return start, end


def _register_and_login(client, admin_headers, username: str) -> tuple[dict, int]:
    """Creates an additional employee account via the real admin-employee
    endpoint - there is no public self-registration in this system."""
    resp = client.post(
        "/api/v1/admin/employees/",
        json={
            "username": username,
            "full_name": username.title(),
            "email": f"{username}@example.com",
            "password": "requesterpass1",
        },
        headers=admin_headers,
    )
    user_id = resp.json()["id"]
    login = client.post(
        "/api/v1/auth/login", data={"username": username, "password": "requesterpass1"}
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, user_id


def _base_payload(traveler_ids=None, **overrides) -> dict:
    start, end = _window()
    payload = {
        "purpose": "Client site visit",
        "destination": "Downtown office",
        "requested_start": start.isoformat(),
        "requested_end": end.isoformat(),
        "traveler_ids": traveler_ids or [],
    }
    payload.update(overrides)
    return payload


# --- creation: auto-include requester, counts, dedupe ---


def test_create_request_auto_includes_requester_as_sole_traveler_by_default(client, requester_headers):
    response = client.post(
        "/api/v1/trip-requests/", json=_base_payload(), headers=requester_headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["passenger_count"] == 1
    assert len(body["travelers"]) == 1
    assert body["travelers"][0]["username"] == "requester1"


def test_create_request_with_multiple_travelers(client, requester_headers, admin_headers):
    bob_headers, bob_id = _register_and_login(client, admin_headers, "bob_trav")
    carol_headers, carol_id = _register_and_login(client, admin_headers, "carol_trav")

    response = client.post(
        "/api/v1/trip-requests/",
        json=_base_payload(traveler_ids=[bob_id, carol_id]),
        headers=requester_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["passenger_count"] == 3  # requester + bob + carol
    usernames = {t["username"] for t in body["travelers"]}
    assert usernames == {"requester1", "bob_trav", "carol_trav"}


def test_passenger_count_always_matches_traveler_list_length(client, requester_headers, admin_headers):
    _, bob_id = _register_and_login(client, admin_headers, "bob_trav2")
    response = client.post(
        "/api/v1/trip-requests/",
        json=_base_payload(traveler_ids=[bob_id]),
        headers=requester_headers,
    )
    body = response.json()
    assert body["passenger_count"] == len(body["travelers"])


def test_duplicate_traveler_id_in_payload_collapses_to_one(client, requester_headers, admin_headers):
    _, bob_id = _register_and_login(client, admin_headers, "bob_trav3")
    response = client.post(
        "/api/v1/trip-requests/",
        json=_base_payload(traveler_ids=[bob_id, bob_id, bob_id]),
        headers=requester_headers,
    )
    body = response.json()
    assert body["passenger_count"] == 2  # requester + bob, once each


def test_requester_listing_own_id_explicitly_does_not_duplicate(client, requester_headers, db_session):
    requester = db_session.query(User).filter(User.username == "requester1").first()
    response = client.post(
        "/api/v1/trip-requests/",
        json=_base_payload(traveler_ids=[requester.id]),
        headers=requester_headers,
    )
    body = response.json()
    assert body["passenger_count"] == 1


# --- validation ---


def test_create_request_rejects_nonexistent_traveler_id(client, requester_headers):
    response = client.post(
        "/api/v1/trip-requests/",
        json=_base_payload(traveler_ids=[999999]),
        headers=requester_headers,
    )
    assert response.status_code == 404


def test_create_request_rejects_inactive_traveler(client, requester_headers, db_session):
    inactive = User(
        username="inactive_emp",
        full_name="Inactive Employee",
        password_hash=hash_password("whatever123"),
        role=UserRole.REQUESTER,
        is_active=False,
    )
    db_session.add(inactive)
    db_session.commit()

    response = client.post(
        "/api/v1/trip-requests/",
        json=_base_payload(traveler_ids=[inactive.id]),
        headers=requester_headers,
    )
    assert response.status_code == 400


def test_create_request_rejects_dispatcher_as_traveler(client, requester_headers, dispatcher_headers, db_session):
    dispatcher = db_session.query(User).filter(User.username == "dispatcher1").first()
    response = client.post(
        "/api/v1/trip-requests/",
        json=_base_payload(traveler_ids=[dispatcher.id]),
        headers=requester_headers,
    )
    assert response.status_code == 400


def test_create_request_end_to_end_time_validation_still_works(client, requester_headers):
    """Regression: adding travelers shouldn't have disturbed the existing
    requested_end > requested_start validation."""
    start, end = _window()
    response = client.post(
        "/api/v1/trip-requests/",
        json=_base_payload(requested_start=end.isoformat(), requested_end=start.isoformat()),
        headers=requester_headers,
    )
    assert response.status_code == 422


# --- employee search ---


def test_search_employees_requires_authentication(client):
    response = client.get("/api/v1/users/")
    assert response.status_code == 401


def test_search_employees_excludes_self_and_dispatchers_and_inactive(
    client, requester_headers, dispatcher_headers, admin_headers, db_session
):
    _, bob_id = _register_and_login(client, admin_headers, "bob_search")
    inactive = User(
        username="inactive_search",
        full_name="Inactive Search",
        password_hash=hash_password("whatever123"),
        role=UserRole.REQUESTER,
        is_active=False,
    )
    db_session.add(inactive)
    db_session.commit()

    response = client.get("/api/v1/users/", headers=requester_headers)
    assert response.status_code == 200
    usernames = {u["username"] for u in response.json()}
    assert "bob_search" in usernames
    assert "requester1" not in usernames  # self excluded
    assert "dispatcher1" not in usernames  # dispatcher excluded
    assert "inactive_search" not in usernames  # inactive excluded


def test_search_employees_filters_by_query(client, requester_headers, admin_headers):
    _register_and_login(client, admin_headers, "findme_zaza")
    _register_and_login(client, admin_headers, "someoneelse_yaya")

    response = client.get("/api/v1/users/", params={"q": "zaza"}, headers=requester_headers)
    usernames = {u["username"] for u in response.json()}
    assert "findme_zaza" in usernames
    assert "someoneelse_yaya" not in usernames


# --- notifications on approval ---


def test_approval_creates_notifications_for_requester_and_travelers(
    client, dispatcher_headers, requester_headers, admin_headers, db_session
):
    _, bob_id = _register_and_login(client, admin_headers, "bob_notif")

    request_resp = client.post(
        "/api/v1/trip-requests/",
        json=_base_payload(traveler_ids=[bob_id]),
        headers=requester_headers,
    )
    request_id = request_resp.json()["id"]

    vehicle_resp = client.post(
        "/api/v1/vehicles/",
        json={"name": "Van Notif", "plate_number": "NOTIF-001", "capacity": 4},
        headers=dispatcher_headers,
    )
    vehicle_id = vehicle_resp.json()["id"]
    driver_resp = client.post(
        "/api/v1/drivers/",
        json={"name": "Driver Notif", "license_number": "DL-NOTIF-001"},
        headers=dispatcher_headers,
    )
    driver_id = driver_resp.json()["id"]

    approve = client.post(
        f"/api/v1/trip-requests/{request_id}/approve",
        json={"vehicle_id": vehicle_id, "driver_id": driver_id},
        headers=dispatcher_headers,
    )
    assert approve.status_code == 200
    trip_id = approve.json()["id"]

    notifications = (
        db_session.query(Notification).filter(Notification.trip_id == trip_id).all()
    )
    assert len(notifications) == 2  # requester + bob
    types = {n.type for n in notifications}
    assert NotificationType.TRIP_APPROVED_REQUESTER in types
    assert NotificationType.TRIP_APPROVED_TRAVELER in types
    assert all(n.status == NotificationStatus.SENT for n in notifications)


def test_notifications_endpoint_returns_only_own_by_default(
    client, dispatcher_headers, requester_headers, admin_headers, db_session
):
    _, bob_id = _register_and_login(client, admin_headers, "bob_notif2")
    bob_headers = client.post(
        "/api/v1/auth/login", data={"username": "bob_notif2", "password": "requesterpass1"}
    ).json()
    bob_auth = {"Authorization": f"Bearer {bob_headers['access_token']}"}

    request_resp = client.post(
        "/api/v1/trip-requests/",
        json=_base_payload(traveler_ids=[bob_id]),
        headers=requester_headers,
    )
    request_id = request_resp.json()["id"]
    vehicle_id = client.post(
        "/api/v1/vehicles/",
        json={"name": "Van Notif2", "plate_number": "NOTIF-002", "capacity": 4},
        headers=dispatcher_headers,
    ).json()["id"]
    driver_id = client.post(
        "/api/v1/drivers/",
        json={"name": "Driver Notif2", "license_number": "DL-NOTIF-002"},
        headers=dispatcher_headers,
    ).json()["id"]
    client.post(
        f"/api/v1/trip-requests/{request_id}/approve",
        json={"vehicle_id": vehicle_id, "driver_id": driver_id},
        headers=dispatcher_headers,
    )

    bob_notifications = client.get("/api/v1/notifications/", headers=bob_auth).json()
    assert len(bob_notifications) == 1
    assert bob_notifications[0]["recipient_user_id"] == bob_id


def test_dispatcher_can_see_all_notifications_with_all_param(
    client, dispatcher_headers, requester_headers
):
    request_resp = client.post(
        "/api/v1/trip-requests/", json=_base_payload(), headers=requester_headers
    )
    request_id = request_resp.json()["id"]
    vehicle_id = client.post(
        "/api/v1/vehicles/",
        json={"name": "Van Notif3", "plate_number": "NOTIF-003", "capacity": 4},
        headers=dispatcher_headers,
    ).json()["id"]
    driver_id = client.post(
        "/api/v1/drivers/",
        json={"name": "Driver Notif3", "license_number": "DL-NOTIF-003"},
        headers=dispatcher_headers,
    ).json()["id"]
    client.post(
        f"/api/v1/trip-requests/{request_id}/approve",
        json={"vehicle_id": vehicle_id, "driver_id": driver_id},
        headers=dispatcher_headers,
    )

    # Dispatcher wasn't a recipient of anything, so without ?all=true they see nothing.
    own = client.get("/api/v1/notifications/", headers=dispatcher_headers).json()
    assert own == []

    everyone = client.get(
        "/api/v1/notifications/", params={"all": "true"}, headers=dispatcher_headers
    ).json()
    assert len(everyone) >= 1


def test_approval_still_succeeds_even_if_notification_step_raises(
    client, dispatcher_headers, requester_headers, monkeypatch
):
    """The spec's explicit requirement: a notification failure must never
    corrupt the trip approval transaction. Simulates a hard failure inside
    notify_trip_approved and confirms the approval still returns 200."""
    from app.services import trip_service

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated notification system outage")

    monkeypatch.setattr(trip_service.notification_service, "notify_trip_approved", _boom)

    request_resp = client.post(
        "/api/v1/trip-requests/", json=_base_payload(), headers=requester_headers
    )
    request_id = request_resp.json()["id"]
    vehicle_id = client.post(
        "/api/v1/vehicles/",
        json={"name": "Van Notif4", "plate_number": "NOTIF-004", "capacity": 4},
        headers=dispatcher_headers,
    ).json()["id"]
    driver_id = client.post(
        "/api/v1/drivers/",
        json={"name": "Driver Notif4", "license_number": "DL-NOTIF-004"},
        headers=dispatcher_headers,
    ).json()["id"]

    approve = client.post(
        f"/api/v1/trip-requests/{request_id}/approve",
        json={"vehicle_id": vehicle_id, "driver_id": driver_id},
        headers=dispatcher_headers,
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

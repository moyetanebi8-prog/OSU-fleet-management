from app.config import settings
from app.models.enums import AlertType

DEVICE_HEADERS = {"X-Device-API-Key": settings.DEVICE_API_KEY}
LIMIT = settings.DEFAULT_SPEED_LIMIT_KMH

SQUARE = [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]


def _create_vehicle(client, dispatcher_headers, plate: str) -> int:
    response = client.post(
        "/api/v1/vehicles/",
        json={"name": f"Vehicle {plate}", "plate_number": plate, "capacity": 4},
        headers=dispatcher_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _ping(client, vehicle_id: int, lat: float, lng: float, speed: float = 20.0):
    return client.post(
        "/api/v1/pings/",
        json={"vehicle_id": vehicle_id, "lat": lat, "lng": lng, "speed": speed},
        headers=DEVICE_HEADERS,
    )


def test_list_alerts_requires_dispatcher(client, requester_headers):
    response = client.get("/api/v1/alerts/", headers=requester_headers)
    assert response.status_code == 403


def test_list_alerts_returns_generated_alerts(client, dispatcher_headers):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "ALR-001")
    _ping(client, vehicle_id, lat=1.0, lng=1.0, speed=LIMIT + 20)

    response = client.get("/api/v1/alerts/", headers=dispatcher_headers)
    assert response.status_code == 200
    body = response.json()
    assert any(a["vehicle_id"] == vehicle_id and a["type"] == "SPEEDING" for a in body)


def test_list_alerts_filters_by_vehicle(client, dispatcher_headers):
    vehicle_a = _create_vehicle(client, dispatcher_headers, "ALR-002")
    vehicle_b = _create_vehicle(client, dispatcher_headers, "ALR-003")
    _ping(client, vehicle_a, lat=1.0, lng=1.0, speed=LIMIT + 20)
    _ping(client, vehicle_b, lat=1.0, lng=1.0, speed=LIMIT + 20)

    response = client.get(
        "/api/v1/alerts/", params={"vehicle_id": vehicle_a}, headers=dispatcher_headers
    )
    body = response.json()
    assert len(body) >= 1
    assert all(a["vehicle_id"] == vehicle_a for a in body)


def test_list_alerts_filters_by_type(client, dispatcher_headers):
    client.post(
        "/api/v1/geofences/",
        json={"name": "Depot Alert Test", "coordinates": SQUARE},
        headers=dispatcher_headers,
    )
    vehicle_id = _create_vehicle(client, dispatcher_headers, "ALR-004")
    _ping(client, vehicle_id, lat=0.5, lng=0.5, speed=LIMIT + 20)  # both geofence entry + speeding

    speeding_only = client.get(
        "/api/v1/alerts/",
        params={"vehicle_id": vehicle_id, "alert_type": "SPEEDING"},
        headers=dispatcher_headers,
    ).json()
    assert all(a["type"] == "SPEEDING" for a in speeding_only)
    assert len(speeding_only) == 1

    entry_only = client.get(
        "/api/v1/alerts/",
        params={"vehicle_id": vehicle_id, "alert_type": "GEOFENCE_ENTRY"},
        headers=dispatcher_headers,
    ).json()
    assert all(a["type"] == "GEOFENCE_ENTRY" for a in entry_only)
    assert len(entry_only) == 1


def test_mark_alert_read(client, dispatcher_headers):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "ALR-005")
    _ping(client, vehicle_id, lat=1.0, lng=1.0, speed=LIMIT + 20)

    unread = client.get(
        "/api/v1/alerts/", params={"vehicle_id": vehicle_id, "is_read": False}, headers=dispatcher_headers
    ).json()
    assert len(unread) == 1
    alert_id = unread[0]["id"]

    response = client.patch(f"/api/v1/alerts/{alert_id}/read", headers=dispatcher_headers)
    assert response.status_code == 200
    assert response.json()["is_read"] is True

    still_unread = client.get(
        "/api/v1/alerts/", params={"vehicle_id": vehicle_id, "is_read": False}, headers=dispatcher_headers
    ).json()
    assert still_unread == []


def test_list_alerts_filters_by_read_true_after_marking(client, dispatcher_headers):
    """The other half of test_mark_alert_read: is_read=True should now
    find it, not just is_read=False failing to."""
    vehicle_id = _create_vehicle(client, dispatcher_headers, "ALR-007")
    _ping(client, vehicle_id, lat=1.0, lng=1.0, speed=LIMIT + 20)

    alert_id = client.get(
        "/api/v1/alerts/", params={"vehicle_id": vehicle_id}, headers=dispatcher_headers
    ).json()[0]["id"]
    client.patch(f"/api/v1/alerts/{alert_id}/read", headers=dispatcher_headers)

    read_alerts = client.get(
        "/api/v1/alerts/", params={"vehicle_id": vehicle_id, "is_read": True}, headers=dispatcher_headers
    ).json()
    assert len(read_alerts) == 1
    assert read_alerts[0]["id"] == alert_id


def test_list_alerts_combined_vehicle_and_type_filter(client, dispatcher_headers):
    vehicle_a = _create_vehicle(client, dispatcher_headers, "ALR-008")
    vehicle_b = _create_vehicle(client, dispatcher_headers, "ALR-009")
    _ping(client, vehicle_a, lat=1.0, lng=1.0, speed=LIMIT + 20)
    _ping(client, vehicle_b, lat=1.0, lng=1.0, speed=LIMIT + 20)

    result = client.get(
        "/api/v1/alerts/",
        params={"vehicle_id": vehicle_a, "alert_type": "SPEEDING"},
        headers=dispatcher_headers,
    ).json()
    assert len(result) == 1
    assert result[0]["vehicle_id"] == vehicle_a
    assert result[0]["type"] == "SPEEDING"


def test_mark_nonexistent_alert_read_404(client, dispatcher_headers):
    response = client.patch("/api/v1/alerts/999999/read", headers=dispatcher_headers)
    assert response.status_code == 404


def test_mark_alert_read_requires_dispatcher(client, dispatcher_headers, requester_headers):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "ALR-006")
    _ping(client, vehicle_id, lat=1.0, lng=1.0, speed=LIMIT + 20)
    alerts = client.get(
        "/api/v1/alerts/", params={"vehicle_id": vehicle_id}, headers=dispatcher_headers
    ).json()
    alert_id = alerts[0]["id"]

    response = client.patch(f"/api/v1/alerts/{alert_id}/read", headers=requester_headers)
    assert response.status_code == 403

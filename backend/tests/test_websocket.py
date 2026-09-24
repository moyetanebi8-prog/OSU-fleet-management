import pytest
from starlette.websockets import WebSocketDisconnect

from app.config import settings

DEVICE_HEADERS = {"X-Device-API-Key": settings.DEVICE_API_KEY}


def _create_vehicle(client, dispatcher_headers, plate: str) -> int:
    response = client.post(
        "/api/v1/vehicles/",
        json={"name": f"Vehicle {plate}", "plate_number": plate, "capacity": 4},
        headers=dispatcher_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _token_from_headers(headers: dict) -> str:
    return headers["Authorization"].split(" ", 1)[1]


def test_websocket_rejects_missing_token(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws"):
            pass


def test_websocket_rejects_invalid_token(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws?token=not-a-real-token"):
            pass


def test_websocket_accepts_valid_dispatcher_token(client, dispatcher_headers):
    token = _token_from_headers(dispatcher_headers)
    with client.websocket_connect(f"/ws?token={token}"):
        pass  # connecting and cleanly closing without error is the assertion


def test_websocket_accepts_valid_requester_token(client, requester_headers):
    """Both roles can connect - filtering what's shown is a frontend concern."""
    token = _token_from_headers(requester_headers)
    with client.websocket_connect(f"/ws?token={token}"):
        pass


def test_websocket_receives_location_update_broadcast(client, dispatcher_headers):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "WS-001")
    token = _token_from_headers(dispatcher_headers)

    with client.websocket_connect(f"/ws?token={token}") as websocket:
        client.post(
            "/api/v1/pings/",
            json={"vehicle_id": vehicle_id, "lat": 12.0, "lng": 34.0, "speed": 20.0},
            headers=DEVICE_HEADERS,
        )
        message = websocket.receive_json()

    assert message["type"] == "location_update"
    assert message["data"]["vehicle_id"] == vehicle_id
    assert message["data"]["lat"] == 12.0
    assert message["data"]["lng"] == 34.0


def test_websocket_receives_alert_broadcast_after_location_update(client, dispatcher_headers):
    vehicle_id = _create_vehicle(client, dispatcher_headers, "WS-002")
    token = _token_from_headers(dispatcher_headers)
    over_limit_speed = settings.DEFAULT_SPEED_LIMIT_KMH + 25

    with client.websocket_connect(f"/ws?token={token}") as websocket:
        client.post(
            "/api/v1/pings/",
            json={"vehicle_id": vehicle_id, "lat": 1.0, "lng": 1.0, "speed": over_limit_speed},
            headers=DEVICE_HEADERS,
        )
        first = websocket.receive_json()
        second = websocket.receive_json()

    assert first["type"] == "location_update"
    assert second["type"] == "alert"
    assert second["data"]["type"] == "SPEEDING"
    assert second["data"]["vehicle_id"] == vehicle_id


def test_websocket_broadcasts_to_multiple_simultaneous_connections(client, dispatcher_headers, requester_headers):
    """ConnectionManager.broadcast fans out to every connection, not just
    the first/most-recent one - both a dispatcher and a requester
    connected at once must each get the same location_update."""
    vehicle_id = _create_vehicle(client, dispatcher_headers, "WS-004")
    dispatcher_token = _token_from_headers(dispatcher_headers)
    requester_token = _token_from_headers(requester_headers)

    with client.websocket_connect(f"/ws?token={dispatcher_token}") as ws_a:
        with client.websocket_connect(f"/ws?token={requester_token}") as ws_b:
            client.post(
                "/api/v1/pings/",
                json={"vehicle_id": vehicle_id, "lat": 5.0, "lng": 6.0, "speed": 15.0},
                headers=DEVICE_HEADERS,
            )
            message_a = ws_a.receive_json()
            message_b = ws_b.receive_json()

    assert message_a["type"] == "location_update"
    assert message_b["type"] == "location_update"
    assert message_a["data"]["vehicle_id"] == vehicle_id
    assert message_b["data"]["vehicle_id"] == vehicle_id

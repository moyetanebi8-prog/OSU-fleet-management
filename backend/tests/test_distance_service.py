import pytest

from app.services.distance_service import calculate_route_distance_km, haversine_km


def test_haversine_known_distance():
    # Approx distance between two points ~1 degree of latitude apart at the
    # equator is close to 111 km.
    distance = haversine_km(0.0, 0.0, 1.0, 0.0)
    assert distance == pytest.approx(111.19, rel=0.01)


def test_haversine_same_point_is_zero():
    assert haversine_km(40.0, -73.0, 40.0, -73.0) == 0.0


def test_route_distance_empty_or_single_point_is_zero():
    assert calculate_route_distance_km([]) == 0.0
    assert calculate_route_distance_km([(40.0, -73.0)]) == 0.0


def test_route_distance_sums_consecutive_segments():
    points = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0)]
    expected = haversine_km(0.0, 0.0, 0.0, 1.0) + haversine_km(0.0, 1.0, 1.0, 1.0)
    assert calculate_route_distance_km(points) == pytest.approx(expected, rel=1e-6)


def test_route_distance_is_not_straight_line_shortcut():
    """A zigzag route must report MORE distance than the direct
    point-to-point distance between its first and last points - this is
    the whole point of summing segments instead of doing endpoint-to-endpoint."""
    zigzag = [(0.0, 0.0), (0.5, 0.0), (0.0, 0.5), (0.5, 0.5)]
    zigzag_distance = calculate_route_distance_km(zigzag)
    direct_distance = haversine_km(0.0, 0.0, 0.5, 0.5)
    assert zigzag_distance > direct_distance

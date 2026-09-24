"""
Route distance calculation (spec sections 18/19).

Deliberately sums the great-circle (Haversine) distance between each
CONSECUTIVE pair of points along a trip's own route, never a single
straight line from the first point to the last - a zigzagging route and a
straight one covering the same two endpoints must not report the same
distance.

Uses plain latitude/longitude columns (see LocationPing), so this is a
pure-Python calculation rather than a PostGIS ST_Length query - both are
"real" distance math; this one doesn't require the points to be first cast
into a PostGIS geometry/geography type.
"""

import math

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def calculate_route_distance_km(points: list[tuple[float, float]]) -> float:
    """`points` must already be ordered by timestamp ascending (oldest
    first). Returns 0.0 for fewer than two points - you can't have a
    distance without at least a start and an end."""
    if len(points) < 2:
        return 0.0

    total = 0.0
    for (lat1, lng1), (lat2, lng2) in zip(points, points[1:]):
        total += haversine_km(lat1, lng1, lat2, lng2)
    return round(total, 3)

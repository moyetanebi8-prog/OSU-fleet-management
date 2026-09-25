from __future__ import annotations

from typing import Any

import httpx


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Identify our application when communicating with Nominatim.
USER_AGENT = "OSU-Fleet-Management-System/1.0"


class GeocodingError(Exception):
    """Raised when a location cannot be converted to coordinates."""


async def geocode_location(location: str) -> tuple[float, float]:
    """
    Convert a human-readable location into latitude and longitude.

    The location is supplied by the requester, so this function works
    with arbitrary locations instead of a hard-coded list of places.
    """

    location = location.strip()

    if not location:
        raise GeocodingError("Location cannot be empty.")

    params = {
        "q": location,
        "format": "jsonv2",
        "limit": 1,
    }

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                NOMINATIM_URL,
                params=params,
                headers=headers,
            )
            response.raise_for_status()

    except httpx.HTTPError as exc:
        raise GeocodingError(
            f"Could not look up location '{location}'."
        ) from exc

    try:
        results: list[dict[str, Any]] = response.json()
    except ValueError as exc:
        raise GeocodingError(
            f"Invalid response received while looking up '{location}'."
        ) from exc

    if not results:
        raise GeocodingError(
            f"Location '{location}' could not be found."
        )

    try:
        latitude = float(results[0]["lat"])
        longitude = float(results[0]["lon"])
    except (KeyError, TypeError, ValueError) as exc:
        raise GeocodingError(
            f"Location '{location}' returned invalid coordinates."
        ) from exc

    return latitude, longitude
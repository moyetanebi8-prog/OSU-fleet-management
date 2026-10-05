#!/usr/bin/env python3
"""
GPS simulator for the Fleet Management System.

Sends GPS pings for one or more vehicles.

If a vehicle has an approved/in-progress trip, the simulator loads the
trip's source and destination from the backend and moves the vehicle
gradually from source toward destination.

The server remains responsible for deciding whether a GPS ping belongs
to an active trip.
"""

import argparse
import asyncio
import math
import os
import random
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime

import httpx


DEFAULT_API_URL = "http://localhost:8000"


def load_device_api_key() -> str | None:
    """Load DEVICE_API_KEY from backend/.env."""
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "backend",
        ".env",
    )

    try:
        with open(env_path, "r", encoding="utf-8") as env_file:
            for line in env_file:
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                if line.startswith("DEVICE_API_KEY="):
                    return (
                        line.split("=", 1)[1]
                        .strip()
                        .strip('"')
                        .strip("'")
                    )

    except FileNotFoundError:
        pass

    return os.getenv("DEVICE_API_KEY")


def log(vehicle_id: int, message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(
        f"[{timestamp}] [vehicle {vehicle_id}] {message}",
        flush=True,
    )


@dataclass
class VehicleSimulator:
    vehicle_id: int
    api_url: str
    api_key: str
    interval: float
    lat: float
    lng: float
    base_speed: float
    speed_variance: float
    pattern: str
    radius_km: float = 0.6

    heading_degrees: float = field(
        default_factory=lambda: random.uniform(0, 360)
    )
    angle_radians: float = 0.0
    center_lat: float = 0.0
    center_lng: float = 0.0
    speed: float = 0.0

    route_start_lat: float | None = None
    route_start_lng: float | None = None
    route_end_lat: float | None = None
    route_end_lng: float | None = None
    route_progress: float = 0.0
    route_trip_id: int | None = None

    def __post_init__(self) -> None:
        self.center_lat = self.lat
        self.center_lng = self.lng

    def _next_speed(self) -> float:
        """Generate a realistic speed."""
        candidate = random.gauss(
            self.base_speed,
            self.speed_variance,
        )
        return max(0.0, candidate)

    def _advance_random_walk(self, distance_km: float) -> None:
        """Move in a gradually changing random direction."""
        self.heading_degrees = (
            self.heading_degrees
            + random.uniform(-25, 25)
        ) % 360

        heading_rad = math.radians(
            self.heading_degrees
        )

        dlat = (
            distance_km / 111.0
        ) * math.cos(heading_rad)

        lng_scale = (
            111.0
            * max(
                math.cos(math.radians(self.lat)),
                0.01,
            )
        )

        dlng = (
            distance_km / lng_scale
        ) * math.sin(heading_rad)

        self.lat += dlat
        self.lng += dlng

    def _advance_circular(self, distance_km: float) -> None:
        """Move around a fixed-radius circle."""
        angular_step = (
            distance_km
            / max(self.radius_km, 0.05)
        )

        self.angle_radians = (
            self.angle_radians
            + angular_step
        ) % (2 * math.pi)

        dlat = (
            self.radius_km / 111.0
        ) * math.sin(self.angle_radians)

        lng_scale = (
            111.0
            * max(
                math.cos(
                    math.radians(self.center_lat)
                ),
                0.01,
            )
        )

        dlng = (
            self.radius_km / lng_scale
        ) * math.cos(self.angle_radians)

        self.lat = self.center_lat + dlat
        self.lng = self.center_lng + dlng

    def advance(self) -> None:
        """Perform normal simulator movement."""
        self.speed = self._next_speed()

        distance_km = (
            self.speed
            * (self.interval / 3600.0)
        )

        if self.pattern == "circular":
            self._advance_circular(distance_km)
        else:
            self._advance_random_walk(distance_km)

    def _advance_toward_destination(
        self,
        distance_km: float,
    ) -> None:
        """Move gradually from current position toward destination."""

        if (
            self.route_end_lat is None
            or self.route_end_lng is None
        ):
            self.advance()
            return

        lat_diff = (
            self.route_end_lat - self.lat
        )

        lng_diff = (
            self.route_end_lng - self.lng
        )

        remaining_km = math.sqrt(
            (lat_diff * 111.0) ** 2
            + (
                lng_diff
                * 111.0
                * max(
                    math.cos(
                        math.radians(self.lat)
                    ),
                    0.01,
                )
            ) ** 2
        )

        if remaining_km <= 0.05:
            self.lat = self.route_end_lat
            self.lng = self.route_end_lng
            self.speed = 0.0
            self.route_progress = 1.0
            return

        movement_km = min(
            distance_km,
            remaining_km,
        )

        ratio = (
            movement_km / remaining_km
        )

        self.lat += lat_diff * ratio
        self.lng += lng_diff * ratio

    async def load_trip_route(
        self,
        client: httpx.AsyncClient,
    ) -> bool:
        """Load the vehicle's current assigned trip."""

        try:
            response = await client.get(
                (
                    f"{self.api_url}/api/v1/vehicles/"
                    f"{self.vehicle_id}/active-trip"
                ),
                headers={
                    "X-Device-API-Key": self.api_key
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()

                trip_id = data.get("trip_id")

                source_lat = data.get(
                    "source_lat"
                )
                source_lng = data.get(
                    "source_lng"
                )

                destination_lat = data.get(
                    "destination_lat"
                )
                destination_lng = data.get(
                    "destination_lng"
                )

                if (
                    source_lat is None
                    or source_lng is None
                    or destination_lat is None
                    or destination_lng is None
                ):
                    log(
                        self.vehicle_id,
                        "Trip route has missing coordinates.",
                    )
                    return False

                self.route_start_lat = float(
                    source_lat
                )
                self.route_start_lng = float(
                    source_lng
                )

                self.route_end_lat = float(
                    destination_lat
                )
                self.route_end_lng = float(
                    destination_lng
                )

                # Only reset to the source when this is
                # a NEW trip.
                if trip_id != self.route_trip_id:
                    self.route_trip_id = trip_id

                    self.lat = (
                        self.route_start_lat
                    )
                    self.lng = (
                        self.route_start_lng
                    )

                    self.route_progress = 0.0

                    log(
                        self.vehicle_id,
                        (
                            f"route loaded for trip "
                            f"{trip_id}: "
                            f"("
                            f"{self.route_start_lat:.5f}, "
                            f"{self.route_start_lng:.5f}"
                            f") -> ("
                            f"{self.route_end_lat:.5f}, "
                            f"{self.route_end_lng:.5f}"
                            f")"
                        ),
                    )

                return True

            if response.status_code == 404:
                if self.route_trip_id is not None:
                    log(
                        self.vehicle_id,
                        (
                            f"trip "
                            f"{self.route_trip_id} "
                            f"is no longer active."
                        ),
                    )

                self.route_trip_id = None
                self.route_start_lat = None
                self.route_start_lng = None
                self.route_end_lat = None
                self.route_end_lng = None
                self.route_progress = 0.0

                return False

            log(
                self.vehicle_id,
                (
                    f"route request failed: "
                    f"{response.status_code} "
                    f"{response.text[:200]}"
                ),
            )

        except httpx.RequestError as exc:
            log(
                self.vehicle_id,
                (
                    f"route request error "
                    f"({exc.__class__.__name__}): "
                    f"{exc}"
                ),
            )

        return False

    async def run(
        self,
        client: httpx.AsyncClient,
        stop_event: asyncio.Event,
    ) -> None:
        """Run the GPS simulator loop."""

        headers = {
            "X-Device-API-Key": self.api_key
        }

        consecutive_failures = 0

        while not stop_event.is_set():

            has_route = await self.load_trip_route(
                client
            )

            self.speed = self._next_speed()

            distance_km = (
                self.speed
                * (self.interval / 3600.0)
            )

            if (
                has_route
                and self.route_trip_id is not None
            ):
                self._advance_toward_destination(
                    distance_km
                )
            elif self.pattern == "circular":
                self._advance_circular(
                    distance_km
                )
            else:
                self._advance_random_walk(
                    distance_km
                )

            payload = {
                "vehicle_id": self.vehicle_id,
                "lat": round(self.lat, 6),
                "lng": round(self.lng, 6),
                "speed": round(self.speed, 1),
            }

            try:
                response = await client.post(
                    f"{self.api_url}/api/v1/pings/",
                    json=payload,
                    headers=headers,
                    timeout=10.0,
                )

                if response.status_code == 201:
                    consecutive_failures = 0

                    log(
                        self.vehicle_id,
                        (
                            f"lat={payload['lat']:.5f} "
                            f"lng={payload['lng']:.5f} "
                            f"speed={payload['speed']:.1f} "
                            f"km/h -> 201 OK"
                        ),
                    )
                else:
                    consecutive_failures += 1

                    log(
                        self.vehicle_id,
                        (
                            f"ping rejected: "
                            f"{response.status_code} "
                            f"{response.text[:200]}"
                        ),
                    )

            except httpx.RequestError as exc:
                consecutive_failures += 1

                log(
                    self.vehicle_id,
                    (
                        f"connection error "
                        f"({exc.__class__.__name__}): "
                        f"{exc}"
                    ),
                )

            wait = self.interval * (
                2 if consecutive_failures >= 3
                else 1
            )

            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=wait,
                )
            except asyncio.TimeoutError:
                pass


def parse_vehicle_ids(
    raw: str,
) -> list[int]:
    """Parse one or more vehicle IDs."""
    try:
        return [
            int(part.strip())
            for part in raw.split(",")
            if part.strip()
        ]

    except ValueError:
        raise argparse.ArgumentTypeError(
            (
                "--vehicle-id must be an integer "
                "or comma-separated integers, "
                f"got: {raw!r}"
            )
        )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Simulate GPS location pings for "
            "one or more fleet vehicles."
        )
    )

    parser.add_argument(
        "--vehicle-id",
        type=str,
        required=True,
        help=(
            "Vehicle ID, or comma-separated list "
            "such as 1,2,3."
        ),
    )

    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=(
            "Backend base URL "
            f"(default: {DEFAULT_API_URL})"
        ),
    )

    parser.add_argument(
        "--api-key",
        default=load_device_api_key(),
        help=(
            "Device API key. Defaults to "
            "DEVICE_API_KEY from backend/.env."
        ),
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help=(
            "Seconds between pings "
            "(default: 5)"
        ),
    )

    parser.add_argument(
        "--start-lat",
        type=float,
        default=7.05,
        help=(
            "Starting latitude "
            "(default: 7.05 - Ethiopia)"
        ),
    )

    parser.add_argument(
        "--start-lng",
        type=float,
        default=38.50,
        help=(
            "Starting longitude "
            "(default: 38.50 - Ethiopia)"
        ),
    )

    parser.add_argument(
        "--base-speed",
        type=float,
        default=40.0,
        help=(
            "Average speed in km/h "
            "(default: 40)"
        ),
    )

    parser.add_argument(
        "--speed-variance",
        type=float,
        default=15.0,
        help=(
            "Speed variance in km/h "
            "(default: 15)"
        ),
    )

    parser.add_argument(
        "--pattern",
        choices=[
            "random-walk",
            "circular",
        ],
        default="random-walk",
        help=(
            "Movement pattern "
            "(default: random-walk)"
        ),
    )

    return parser.parse_args()


async def main() -> None:
    """Start the simulator."""

    args = parse_args()

    if not args.api_key:
        print(
            (
                "Error: no device API key provided. "
                "Pass --api-key or set DEVICE_API_KEY "
                "in backend/.env."
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    vehicle_ids = parse_vehicle_ids(
        args.vehicle_id
    )

    stop_event = asyncio.Event()

    def handle_signal() -> None:
        print(
            "\nShutting down simulator...",
            flush=True,
        )
        stop_event.set()

    loop = asyncio.get_running_loop()

    for sig in (
        signal.SIGINT,
        signal.SIGTERM,
    ):
        try:
            loop.add_signal_handler(
                sig,
                handle_signal,
            )
        except NotImplementedError:
            pass

    simulators = [
        VehicleSimulator(
            vehicle_id=vid,
            api_url=args.api_url.rstrip("/"),
            api_key=args.api_key,
            interval=args.interval,
            lat=args.start_lat,
            lng=args.start_lng,
            base_speed=args.base_speed,
            speed_variance=args.speed_variance,
            pattern=args.pattern,
        )
        for vid in vehicle_ids
    ]

    print(
        (
            f"Starting simulator for vehicle(s) "
            f"{vehicle_ids} against {args.api_url} "
            f"(pattern={args.pattern}, "
            f"interval={args.interval}s). "
            "Press Ctrl+C to stop."
        )
    )

    async with httpx.AsyncClient() as client:
        try:
            await asyncio.gather(
                *(
                    sim.run(
                        client,
                        stop_event,
                    )
                    for sim in simulators
                )
            )
        except KeyboardInterrupt:
            stop_event.set()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
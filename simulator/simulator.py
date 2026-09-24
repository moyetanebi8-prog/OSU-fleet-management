#!/usr/bin/env python3
"""
GPS simulator for the Fleet Management System.

Sends realistic, continuously-updating GPS pings for one or more vehicles
to POST /api/v1/pings/. Uses asyncio + httpx (async client - never
synchronous `requests` calls inside the async loop, per spec section 39).

IMPORTANT: this simulator has NO concept of trips. It only ever sends
{vehicle_id, lat, lng, speed} - it does not know or care whether the
vehicle is currently on a trip, and it never sends a trip_id (the ping
schema doesn't even accept one). Whether a ping belongs to an active trip
is decided entirely server-side (see backend/app/services/gps_service.py).
This is deliberate: the simulator plays the role of a real GPS tracking
device, which has no idea what a "trip" is either.

Usage:
    python simulator.py --vehicle-id 1
    python simulator.py --vehicle-id 1,2,3          # multiple vehicles at once
    python simulator.py --vehicle-id 2 --pattern circular --interval 3
    python simulator.py --vehicle-id 1 --start-lat 51.5074 --start-lng -0.1278

Run one instance per terminal, or pass a comma-separated list to simulate
several vehicles concurrently from a single process.
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
EARTH_RADIUS_KM = 6371.0088


def log(vehicle_id: int, message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [vehicle {vehicle_id}] {message}", flush=True)


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

    heading_degrees: float = field(default_factory=lambda: random.uniform(0, 360))
    angle_radians: float = 0.0
    center_lat: float = 0.0
    center_lng: float = 0.0
    speed: float = 0.0

    def __post_init__(self) -> None:
        self.center_lat = self.lat
        self.center_lng = self.lng

    def _next_speed(self) -> float:
        # Gaussian noise around the configured base speed, floored at 0 -
        # occasionally drifts above a typical speed limit on purpose, so
        # the backend's speed-alert detection has something real to catch.
        candidate = random.gauss(self.base_speed, self.speed_variance)
        return max(0.0, candidate)

    def _advance_random_walk(self, distance_km: float) -> None:
        # Bounded heading drift keeps movement looking like a vehicle
        # following roads/turns rather than teleporting randomly.
        self.heading_degrees = (self.heading_degrees + random.uniform(-25, 25)) % 360
        heading_rad = math.radians(self.heading_degrees)

        dlat = (distance_km / 111.0) * math.cos(heading_rad)
        lng_scale = 111.0 * max(math.cos(math.radians(self.lat)), 0.01)
        dlng = (distance_km / lng_scale) * math.sin(heading_rad)

        self.lat += dlat
        self.lng += dlng

    def _advance_circular(self, distance_km: float) -> None:
        # Loops around a fixed-radius circle - handy for demoing geofence
        # enter/exit alerts repeatedly without manual intervention.
        angular_step = distance_km / max(self.radius_km, 0.05)
        self.angle_radians = (self.angle_radians + angular_step) % (2 * math.pi)

        dlat = (self.radius_km / 111.0) * math.sin(self.angle_radians)
        lng_scale = 111.0 * max(math.cos(math.radians(self.center_lat)), 0.01)
        dlng = (self.radius_km / lng_scale) * math.cos(self.angle_radians)

        self.lat = self.center_lat + dlat
        self.lng = self.center_lng + dlng

    def advance(self) -> None:
        self.speed = self._next_speed()
        distance_km = self.speed * (self.interval / 3600.0)

        if self.pattern == "circular":
            self._advance_circular(distance_km)
        else:
            self._advance_random_walk(distance_km)

    async def run(self, client: httpx.AsyncClient, stop_event: asyncio.Event) -> None:
        headers = {"X-Device-API-Key": self.api_key}
        consecutive_failures = 0

        while not stop_event.is_set():
            self.advance()
            payload = {
                "vehicle_id": self.vehicle_id,
                "lat": round(self.lat, 6),
                "lng": round(self.lng, 6),
                "speed": round(self.speed, 1),
            }

            try:
                response = await client.post(
                    f"{self.api_url}/api/v1/pings/", json=payload, headers=headers, timeout=10.0
                )
                if response.status_code == 201:
                    consecutive_failures = 0
                    log(
                        self.vehicle_id,
                        f"lat={payload['lat']:.5f} lng={payload['lng']:.5f} "
                        f"speed={payload['speed']:.1f} km/h -> 201 OK",
                    )
                else:
                    consecutive_failures += 1
                    log(
                        self.vehicle_id,
                        f"ping rejected: {response.status_code} {response.text[:200]}",
                    )
            except httpx.RequestError as exc:
                consecutive_failures += 1
                log(self.vehicle_id, f"connection error ({exc.__class__.__name__}): {exc}")

            # Back off a bit on repeated failures instead of hammering an
            # unreachable server every `interval` seconds forever.
            wait = self.interval * (2 if consecutive_failures >= 3 else 1)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=wait)
            except asyncio.TimeoutError:
                pass


def parse_vehicle_ids(raw: str) -> list[int]:
    try:
        return [int(part.strip()) for part in raw.split(",") if part.strip()]
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--vehicle-id must be an integer or comma-separated integers, got: {raw!r}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate GPS location pings for one or more fleet vehicles."
    )
    parser.add_argument(
        "--vehicle-id",
        type=str,
        required=True,
        help="Vehicle ID, or comma-separated list to simulate several at once (e.g. 1,2,3).",
    )
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help=f"Backend base URL (default: {DEFAULT_API_URL})")
    parser.add_argument(
        "--api-key",
        default=os.environ.get("DEVICE_API_KEY"),
        help="Device API key. Defaults to the DEVICE_API_KEY environment variable.",
    )
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between pings (default: 5)")
    parser.add_argument("--start-lat", type=float, default=37.7749, help="Starting latitude (default: 37.7749)")
    parser.add_argument("--start-lng", type=float, default=-122.4194, help="Starting longitude (default: -122.4194)")
    parser.add_argument("--base-speed", type=float, default=40.0, help="Average speed in km/h (default: 40)")
    parser.add_argument(
        "--speed-variance", type=float, default=15.0, help="Speed variance in km/h (default: 15)"
    )
    parser.add_argument(
        "--pattern",
        choices=["random-walk", "circular"],
        default="random-walk",
        help="Movement pattern (default: random-walk)",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    if not args.api_key:
        print(
            "Error: no device API key provided. Pass --api-key or set the "
            "DEVICE_API_KEY environment variable (must match backend/.env).",
            file=sys.stderr,
        )
        sys.exit(1)

    vehicle_ids = parse_vehicle_ids(args.vehicle_id)
    stop_event = asyncio.Event()

    def handle_signal() -> None:
        print("\nShutting down simulator…", flush=True)
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            # add_signal_handler isn't available on Windows - Ctrl+C still
            # raises KeyboardInterrupt, handled below.
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
        f"Starting simulator for vehicle(s) {vehicle_ids} against {args.api_url} "
        f"(pattern={args.pattern}, interval={args.interval}s). Press Ctrl+C to stop."
    )

    async with httpx.AsyncClient() as client:
        try:
            await asyncio.gather(*(sim.run(client, stop_event) for sim in simulators))
        except KeyboardInterrupt:
            stop_event.set()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")

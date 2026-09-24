"""
FastAPI application entrypoint.

Run locally with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    admin,
    alerts,
    auth,
    drivers,
    geofences,
    health,
    notifications,
    pings,
    trip_requests,
    trips,
    users,
    vehicles,
    websocket,
)

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
# Phase 13 (WebSocket real-time tracking) completed the original 18-phase
# build. `users` and `notifications` were added afterward for the traveler-
# selection feature (explicit employee search + notification history).
app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(vehicles.router, prefix=settings.API_V1_PREFIX)
app.include_router(drivers.router, prefix=settings.API_V1_PREFIX)
app.include_router(trip_requests.router, prefix=settings.API_V1_PREFIX)
app.include_router(trips.router, prefix=settings.API_V1_PREFIX)
app.include_router(pings.router, prefix=settings.API_V1_PREFIX)
app.include_router(geofences.router, prefix=settings.API_V1_PREFIX)
app.include_router(alerts.router, prefix=settings.API_V1_PREFIX)
app.include_router(notifications.router, prefix=settings.API_V1_PREFIX)
# No prefix - the spec and the frontend's Vite proxy both expect a bare /ws.
app.include_router(websocket.router)


@app.get("/")
def root() -> dict:
    return {
        "service": settings.APP_NAME,
        "status": "running",
        "docs": "/api/docs",
    }

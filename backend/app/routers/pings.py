from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.database import get_db
from app.dependencies.device import require_device_api_key
from app.schemas.alert import AlertResponse
from app.schemas.ping import PingCreate, PingResponse
from app.services import gps_service
from app.websocket.manager import manager

router = APIRouter(prefix="/pings", tags=["pings"], dependencies=[Depends(require_device_api_key)])


@router.post("/", response_model=PingResponse, status_code=status.HTTP_201_CREATED)
async def create_ping(payload: PingCreate, db: Session = Depends(get_db)) -> PingResponse:
    """
    async because broadcasting over WebSocket requires it, while the actual
    DB work (gps_service.record_ping) is synchronous SQLAlchemy - so that
    part runs in a threadpool to avoid blocking the event loop, and only
    the broadcast itself runs directly on the loop.
    """
    try:
        ping, new_alerts = await run_in_threadpool(
            gps_service.record_ping, db, payload.vehicle_id, payload.lat, payload.lng, payload.speed
        )
    except gps_service.VehicleNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ping_response = PingResponse.model_validate(ping)
    await manager.broadcast({"type": "location_update", "data": ping_response.model_dump(mode="json")})

    for alert in new_alerts:
        alert_response = AlertResponse.model_validate(alert)
        await manager.broadcast({"type": "alert", "data": alert_response.model_dump(mode="json")})

    return ping_response

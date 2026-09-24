"""
The `/ws` endpoint (spec section 16). Mounted at the bare path (no
/api/v1 prefix) to match the spec exactly and the frontend's Vite dev
proxy (see frontend/vite.config.js), which already proxies `/ws` as-is.

Browsers' native WebSocket API can't set an Authorization header, so the
JWT is passed as a query parameter instead: `/ws?token=<access_token>`.
Uses the same `get_db` dependency as every REST route (rather than
manually opening a session) so it participates correctly in the same
request-scoped session machinery - including, importantly, the test
suite's dependency override.
"""

from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.orm import Session
from starlette import status as ws_status
from starlette.websockets import WebSocketDisconnect

from app.database import get_db
from app.models.user import User
from app.services.auth import JWTError, decode_access_token
from app.websocket.manager import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = decode_access_token(token)
    except JWTError:
        await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
        return

    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first() if username else None
    if user is None or not user.is_active:
        await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    try:
        while True:
            # We don't expect meaningful messages FROM the client, but we
            # must keep receiving to promptly detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

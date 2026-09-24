"""
WebSocket connection manager (spec section 16).

All authenticated connections - both requester and dispatcher tokens -
receive every broadcast; filtering to "what's relevant to display" (e.g. a
requester's UI only caring about their own active trip's vehicle) is left
to the frontend. This keeps the server side simple, and fleet broadcast
volume is small even for a large fleet compared to, say, chat fan-out.
"""

import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        if not self._connections:
            return

        payload = json.dumps(message, default=str)
        stale: list[WebSocket] = []

        for connection in list(self._connections):
            try:
                await connection.send_text(payload)
            except Exception:  # noqa: BLE001 - any send failure means a dead connection
                stale.append(connection)

        for connection in stale:
            self.disconnect(connection)


# Single process-wide instance. Fine for a single-process deployment; a
# multi-instance deployment would need a shared pub/sub backend (e.g.
# Redis) instead - noted here rather than silently pretending this scales
# past one process.
manager = ConnectionManager()

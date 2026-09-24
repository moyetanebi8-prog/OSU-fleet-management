"""
GPS-sending devices (vehicles, the simulator) aren't `requester` or
`dispatcher` user accounts - they authenticate with a single shared key
instead of a JWT. Kept in its own module rather than dependencies/auth.py
so the two auth models don't get tangled together.
"""

from fastapi import Header, HTTPException, status

from app.config import settings


def require_device_api_key(x_device_api_key: str | None = Header(default=None)) -> None:
    if x_device_api_key != settings.DEVICE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid device API key.",
        )

"""Health check endpoint used for liveness/readiness probes and smoke tests."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    return {"status": "ok"}

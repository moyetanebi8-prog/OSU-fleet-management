from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.enums import UserRole
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=list[NotificationResponse])
def list_notifications(
    all_recipients: bool = Query(default=False, alias="all"),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Notification]:
    """
    By default, everyone (requester or dispatcher) sees only notifications
    addressed to them. A dispatcher can pass ?all=true to see every
    notification system-wide - useful for confirming delivery/failure
    across a whole trip approval, not just their own.
    """
    query = db.query(Notification)

    if not (all_recipients and current_user.role == UserRole.DISPATCHER):
        query = query.filter(Notification.recipient_user_id == current_user.id)

    return query.order_by(Notification.created_at.desc()).limit(limit).all()

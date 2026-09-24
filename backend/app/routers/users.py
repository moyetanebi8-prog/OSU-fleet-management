from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserSummary

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserSummary])
def search_employees(
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[User]:
    """
    Powers the traveler-selection search box (feature spec section 2).
    "Employee" in this system means an active `requester`-role account -
    there's no separate employee directory - so this only ever returns
    people who could legitimately be selected as a traveler. Dispatcher
    accounts and inactive accounts never appear here, and the current
    caller is excluded since the frontend shows them separately as "You".

    Available to any authenticated user (a requester needs this to build
    a trip request) - not dispatcher-only.
    """
    query = db.query(User).filter(
        User.role == UserRole.REQUESTER,
        User.is_active.is_(True),
        User.id != current_user.id,
    )

    if q:
        pattern = f"%{q}%"
        query = query.filter(or_(User.username.ilike(pattern), User.full_name.ilike(pattern)))

    return query.order_by(User.full_name).limit(limit).all()

"""
FastAPI dependencies for authentication and role-based authorization.

CRITICAL: the backend is the only source of truth for authorization.
`get_current_user` re-fetches the user from the database on every request
(not just trusting the JWT payload) so a deactivated account is rejected
immediately even with a still-valid token. `require_dispatcher` /
`require_requester` are what actually protect endpoints - never rely on the
frontend hiding a button.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.services.auth import JWTError, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise _CREDENTIALS_ERROR

    username: str | None = payload.get("sub")
    if username is None:
        raise _CREDENTIALS_ERROR

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise _CREDENTIALS_ERROR

    return user


def require_dispatcher(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.DISPATCHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires dispatcher privileges.",
        )
    return current_user


def require_requester(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.REQUESTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action is only available to requester accounts.",
        )
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires administrator privileges.",
        )
    return current_user

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import TokenResponse, UserResponse
from app.services.auth import authenticate_user, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

# NOTE: there is intentionally no public /register endpoint. Employee
# (requester) accounts are created only by an admin - one at a time via
# POST /api/v1/admin/employees/, or in bulk via
# POST /api/v1/admin/employees/import-csv. Dispatcher and admin accounts
# are created via scripts/create_dispatcher.py / scripts/create_admin.py,
# or by an existing admin via POST /api/v1/admin/accounts/. This is a
# deliberate access-control decision: only pre-provisioned company
# accounts can ever sign in.


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Uses the standard OAuth2 password-flow form (username + password as
    form fields) so this endpoint works out of the box with the Swagger UI
    "Authorize" button as well as a normal frontend login form submission.
    Works for requester, dispatcher, and admin accounts alike - the role
    difference is in what the resulting token is authorized to do, not in
    how login happens.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=user.username, role=user.role.value)
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user

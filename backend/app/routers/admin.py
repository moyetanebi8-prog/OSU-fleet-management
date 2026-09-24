from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import (
    CsvImportResult,
    DispatcherOrAdminCreate,
    EmployeeCreate,
    EmployeeCreateResult,
    UserManagementResponse,
    UserStatusUpdate,
)
from app.services import employee_service
from app.services.auth import hash_password

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post(
    "/employees/", response_model=EmployeeCreateResult, status_code=status.HTTP_201_CREATED
)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)) -> EmployeeCreateResult:
    """Adds a single employee (requester account). If no password is
    given, a secure temporary one is generated and returned here once -
    it is never retrievable again after this response, so the admin must
    record/relay it now (or rely on the onboarding email, if SMTP is
    configured)."""
    try:
        return employee_service.create_employee(
            db,
            username=payload.username,
            full_name=payload.full_name,
            email=payload.email,
            password=payload.password,
        )
    except employee_service.DuplicateEmployeeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/employees/import-csv", response_model=CsvImportResult)
async def import_employees_csv(
    file: UploadFile, db: Session = Depends(get_db)
) -> CsvImportResult:
    """
    CSV columns required: username, full_name, email. Optional: password
    (auto-generated per-row if omitted). Bad rows are reported individually
    in `errors` - one duplicate or malformed row doesn't fail the whole
    import.
    """
    content = await file.read()
    try:
        return employee_service.import_employees_from_csv(db, content)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post(
    "/accounts/", response_model=UserManagementResponse, status_code=status.HTTP_201_CREATED
)
def create_dispatcher_or_admin_account(
    payload: DispatcherOrAdminCreate, db: Session = Depends(get_db)
) -> User:
    """
    Lets an existing admin create additional dispatcher or admin accounts
    through the panel - this complements, but does not replace,
    scripts/create_admin.py / scripts/create_dispatcher.py, which remain
    the only way to bootstrap the very first admin account on a fresh
    install (you need an admin to use this endpoint at all).
    """
    try:
        payload.validate_role()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username is already taken.")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered.")

    user = User(
        username=payload.username,
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users/", response_model=list[UserManagementResponse])
def list_users(
    role: UserRole | None = None,
    db: Session = Depends(get_db),
) -> list[User]:
    query = db.query(User)
    if role is not None:
        query = query.filter(User.role == role)
    return query.order_by(User.created_at.desc()).all()


@router.patch("/users/{user_id}/status", response_model=UserManagementResponse)
def update_user_status(
    user_id: int, payload: UserStatusUpdate, db: Session = Depends(get_db)
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return user

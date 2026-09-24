from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_dispatcher
from app.models.driver import Driver
from app.schemas.driver import (
    DriverCreate,
    DriverResponse,
    DriverStatusUpdate,
    DriverUpdate,
)
from app.services.driver_service import InvalidStatusTransition, change_driver_status

router = APIRouter(
    prefix="/drivers", tags=["drivers"], dependencies=[Depends(require_dispatcher)]
)


def _get_driver_or_404(db: Session, driver_id: int) -> Driver:
    driver = db.get(Driver, driver_id)
    if driver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found.")
    return driver


@router.get("/", response_model=list[DriverResponse])
def list_drivers(db: Session = Depends(get_db)) -> list[Driver]:
    return db.query(Driver).order_by(Driver.id).all()


@router.post("/", response_model=DriverResponse, status_code=status.HTTP_201_CREATED)
def create_driver(payload: DriverCreate, db: Session = Depends(get_db)) -> Driver:
    if db.query(Driver).filter(Driver.license_number == payload.license_number).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"License number '{payload.license_number}' is already registered.",
        )

    driver = Driver(name=payload.name, license_number=payload.license_number, email=payload.email)
    db.add(driver)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"License number '{payload.license_number}' is already registered.",
        )
    db.refresh(driver)
    return driver


@router.get("/{driver_id}", response_model=DriverResponse)
def get_driver(driver_id: int, db: Session = Depends(get_db)) -> Driver:
    return _get_driver_or_404(db, driver_id)


@router.put("/{driver_id}", response_model=DriverResponse)
def update_driver(driver_id: int, payload: DriverUpdate, db: Session = Depends(get_db)) -> Driver:
    driver = _get_driver_or_404(db, driver_id)

    conflict = (
        db.query(Driver)
        .filter(Driver.license_number == payload.license_number, Driver.id != driver_id)
        .first()
    )
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"License number '{payload.license_number}' is already registered.",
        )

    driver.name = payload.name
    driver.license_number = payload.license_number
    driver.email = payload.email
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"License number '{payload.license_number}' is already registered.",
        )
    db.refresh(driver)
    return driver


@router.patch("/{driver_id}/status", response_model=DriverResponse)
def update_driver_status(
    driver_id: int, payload: DriverStatusUpdate, db: Session = Depends(get_db)
) -> Driver:
    driver = _get_driver_or_404(db, driver_id)
    try:
        return change_driver_status(db, driver, payload.status)
    except InvalidStatusTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

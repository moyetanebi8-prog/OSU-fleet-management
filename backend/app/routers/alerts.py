from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_dispatcher
from app.models.alert import Alert
from app.models.enums import AlertType
from app.schemas.alert import AlertResponse

router = APIRouter(prefix="/alerts", tags=["alerts"], dependencies=[Depends(require_dispatcher)])


@router.get("/", response_model=list[AlertResponse])
def list_alerts(
    vehicle_id: int | None = None,
    alert_type: AlertType | None = None,
    is_read: bool | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[Alert]:
    query = db.query(Alert)
    if vehicle_id is not None:
        query = query.filter(Alert.vehicle_id == vehicle_id)
    if alert_type is not None:
        query = query.filter(Alert.type == alert_type)
    if is_read is not None:
        query = query.filter(Alert.is_read == is_read)

    return query.order_by(Alert.timestamp.desc(), Alert.id.desc()).limit(limit).all()


@router.patch("/{alert_id}/read", response_model=AlertResponse)
def mark_alert_read(alert_id: int, db: Session = Depends(get_db)) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    alert.is_read = True
    db.commit()
    db.refresh(alert)
    return alert

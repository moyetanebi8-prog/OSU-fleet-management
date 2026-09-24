from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2.shape import from_shape
from shapely.errors import ShapelyError
from shapely.geometry import Polygon
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_dispatcher
from app.models.geofence import Geofence
from app.schemas.geofence import GeofenceCreate, GeofenceResponse

router = APIRouter(
    prefix="/geofences", tags=["geofences"], dependencies=[Depends(require_dispatcher)]
)


@router.get("/", response_model=list[GeofenceResponse])
def list_geofences(db: Session = Depends(get_db)) -> list[GeofenceResponse]:
    geofences = db.query(Geofence).order_by(Geofence.id).all()
    return [GeofenceResponse.from_model(g) for g in geofences]


@router.post("/", response_model=GeofenceResponse, status_code=status.HTTP_201_CREATED)
def create_geofence(payload: GeofenceCreate, db: Session = Depends(get_db)) -> GeofenceResponse:
    try:
        polygon = Polygon(payload.coordinates)
    except ShapelyError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Coordinates do not form a valid polygon.",
        )

    if not polygon.is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Polygon is self-intersecting or otherwise invalid.",
        )

    geofence = Geofence(
        name=payload.name,
        description=payload.description,
        geometry=from_shape(polygon, srid=4326),
        is_active=True,
    )
    db.add(geofence)
    db.commit()
    db.refresh(geofence)
    return GeofenceResponse.from_model(geofence)

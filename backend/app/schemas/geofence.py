from datetime import datetime

from geoalchemy2.shape import to_shape
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.geofence import Geofence


class GeofenceCreate(BaseModel):
    """`coordinates` is a polygon ring as [lng, lat] pairs (GeoJSON
    convention), first and last point identical (closed ring), at least
    4 points (3 distinct corners + the closing point)."""

    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=500)
    coordinates: list[tuple[float, float]] = Field(min_length=4)

    @model_validator(mode="after")
    def _validate_ring(self) -> "GeofenceCreate":
        if self.coordinates[0] != self.coordinates[-1]:
            raise ValueError(
                "Polygon coordinates must form a closed ring "
                "(the first and last points must be identical)."
            )
        for lng, lat in self.coordinates:
            if not (-180 <= lng <= 180):
                raise ValueError(f"Invalid longitude: {lng}")
            if not (-90 <= lat <= 90):
                raise ValueError(f"Invalid latitude: {lat}")
        return self


class GeofenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    coordinates: list[list[float]]
    is_active: bool
    created_at: datetime

    @classmethod
    def from_model(cls, geofence: Geofence) -> "GeofenceResponse":
        shape = to_shape(geofence.geometry)
        coordinates = [[float(x), float(y)] for x, y in shape.exterior.coords]
        return cls(
            id=geofence.id,
            name=geofence.name,
            description=geofence.description,
            coordinates=coordinates,
            is_active=geofence.is_active,
            created_at=geofence.created_at,
        )

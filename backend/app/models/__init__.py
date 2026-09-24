"""
Importing every model module here ensures Base.metadata is fully populated
before Alembic (or Base.metadata.create_all in tests) inspects it. Order
matters only for readability, not for SQLAlchemy - relationships are
resolved lazily via string references.
"""

from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.driver import Driver
from app.models.trip_request import TripRequest
from app.models.trip_request_traveler import TripRequestTraveler
from app.models.trip import Trip
from app.models.location_ping import LocationPing
from app.models.alert import Alert
from app.models.geofence import Geofence
from app.models.geofence_state import VehicleGeofenceState
from app.models.notification import Notification

__all__ = [
    "User",
    "Vehicle",
    "Driver",
    "TripRequest",
    "TripRequestTraveler",
    "Trip",
    "LocationPing",
    "Alert",
    "Geofence",
    "VehicleGeofenceState",
    "Notification",
]

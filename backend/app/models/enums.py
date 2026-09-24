"""
Shared enum types for the domain model.

Using Python enums backed by SQLAlchemy Enum columns means invalid status
values are rejected at the database level (native CHECK/ENUM constraint),
not just in application code - this is what section 7/8/9 of the spec
means by "do not allow arbitrary invalid statuses".
"""

import enum


class UserRole(str, enum.Enum):
    REQUESTER = "requester"
    DISPATCHER = "dispatcher"
    ADMIN = "admin"


class VehicleStatus(str, enum.Enum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    MAINTENANCE = "maintenance"
    INACTIVE = "inactive"


class DriverStatus(str, enum.Enum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    DRIVING = "driving"
    INACTIVE = "inactive"


class TripRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"


class TripStatus(str, enum.Enum):
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AlertType(str, enum.Enum):
    SPEEDING = "SPEEDING"
    GEOFENCE_EXIT = "GEOFENCE_EXIT"
    GEOFENCE_ENTRY = "GEOFENCE_ENTRY"
    SYSTEM = "SYSTEM"


class NotificationType(str, enum.Enum):
    TRIP_APPROVED_REQUESTER = "TRIP_APPROVED_REQUESTER"
    TRIP_APPROVED_TRAVELER = "TRIP_APPROVED_TRAVELER"
    TRIP_APPROVED_DRIVER = "TRIP_APPROVED_DRIVER"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"

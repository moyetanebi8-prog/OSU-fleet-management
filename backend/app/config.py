"""
Centralized application configuration.

All configuration is loaded from environment variables (via .env in local
development). Nothing sensitive is hardcoded. See .env.example at the
project root for the full list of variables this application expects.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "Fleet Management System API"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # --- Database ---
    DATABASE_URL: str = (
        "postgresql+psycopg://fms_user:fms_password@localhost:5432/fms_db"
    )

    # --- Auth / JWT ---
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Device ingestion (GPS pings) ---
    # Vehicles/the GPS simulator authenticate with this shared key instead
    # of a user JWT - they aren't "requester" or "dispatcher" accounts.
    DEVICE_API_KEY: str = "dev-device-key-change-me"

    # --- Business rules ---
    DEFAULT_SPEED_LIMIT_KMH: float = 80.0
    GEOFENCE_CHECK_ENABLED: bool = True

    # --- Email (SMTP) ---
    # Used for driver assignment notifications, traveler/requester
    # notifications, and employee-onboarding emails. If SMTP_HOST is left
    # empty, email_service.py raises a clear, loud error on send rather
    # than pretending to succeed - see app/services/email_service.py.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: str = "no-reply@example.com"
    SMTP_FROM_NAME: str = "Fleet Management System"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton so we don't re-parse env vars on every call."""
    return Settings()


settings = get_settings()

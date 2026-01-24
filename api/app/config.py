import os
from functools import lru_cache
from typing import Any

from pydantic import HttpUrl, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """API settings."""

    # App
    environment: str = "development"
    frontend_origin: HttpUrl
    backend_origin: HttpUrl

    # OIDC
    keycloak_url: HttpUrl
    keycloak_realm: str = "eigentask"
    keycloak_client_id: str = "eigentask"
    keycloak_client_secret: str | None = None
    callback_url: HttpUrl

    @field_validator("frontend_origin", "backend_origin", "keycloak_url", "callback_url", mode="before")
    @classmethod
    def validate_url(cls, v: Any) -> Any:
        """Allow string URLs to be converted to HttpUrl."""
        if isinstance(v, str):
            return v
        return v

    class Config:
        """Pydantic configuration."""

        # Default values for URLs
        env_file = ".env"
        extra = "ignore"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize settings with defaults."""
        # Set defaults if not provided
        if "frontend_origin" not in kwargs:
            kwargs["frontend_origin"] = "http://localhost:5173"
        if "backend_origin" not in kwargs:
            kwargs["backend_origin"] = "http://localhost:8000"
        if "keycloak_url" not in kwargs:
            kwargs["keycloak_url"] = "https://auth.eigentask.com"
        if "callback_url" not in kwargs:
            kwargs["callback_url"] = "http://localhost:8000/auth/callback"
        super().__init__(**kwargs)

    # Session/Cookies
    session_secret: str = os.getenv("SESSION_SECRET", "dev-insecure-session-secret")
    cookie_domain: str | None = None
    cookie_secure: bool = False

    # Redis / Sessions
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    session_cookie_name: str = os.getenv("SESSION_COOKIE_NAME", "sid")
    redis_session_ttl_seconds: int = int(os.getenv("SESSION_TTL_SECONDS", str(60 * 60 * 24 * 7)))
    redis_session_prefix: str = os.getenv("SESSION_PREFIX", "sess:")

    # PostgreSQL
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/eigentask")


@lru_cache(1)
def get_settings() -> Settings:
    """Get API settings.

    This function uses lru_cache to cache the settings object to prevent repeated parsing.

    Returns:
        Settings: API settings.

    """
    return Settings()

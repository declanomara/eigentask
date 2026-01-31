"""Pytest fixtures for integration testing."""

from collections.abc import AsyncIterator, Iterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fakeredis import FakeAsyncRedis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from starlette.middleware.sessions import SessionMiddleware

from app.config import Settings, get_settings
from app.core.db import Base, get_session
from app.models import Task  # noqa: F401 - Import to register models with Base
from app.routers import auth as auth_router
from app.routers import root as root_router
from app.routers import tasks as tasks_router
from app.routers import users as users_router


@pytest.fixture
def test_settings(tmp_path_factory) -> Settings:  # type: ignore[no-untyped-def]
    """Create test settings with temporary file-based SQLite database."""
    # Create a temporary database file for the test session
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    # Use kwargs to bypass type checking for URL strings
    settings_dict = {
        "environment": "test",
        "database_url": f"sqlite+aiosqlite:///{db_path}",
        "redis_url": "redis://localhost:6379/15",
        "frontend_origin": "http://localhost:3000",
        "backend_origin": "http://localhost:8000",
        "keycloak_url": "https://keycloak.test",
        "keycloak_realm": "test-realm",
        "keycloak_client_id": "test-client",
        "callback_url": "http://localhost:8000/auth/callback",
        "session_secret": "test-secret-key-for-sessions",
        "cookie_secure": False,
    }
    return Settings(**settings_dict)  # type: ignore[arg-type]


@pytest_asyncio.fixture
async def test_engine(test_settings: Settings) -> AsyncIterator[AsyncEngine]:
    """Create a test database engine."""
    engine = create_async_engine(
        test_settings.database_url,
        poolclass=NullPool,
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Create a database session for a test.

    Creates a new connection and session for each test, with automatic
    rollback after the test completes.
    """
    async with test_engine.connect() as connection:
        # Begin a transaction
        transaction = await connection.begin()

        # Create a session bound to the connection
        async_session_maker = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with async_session_maker() as session:
            yield session

            # Rollback the transaction after the test
            await transaction.rollback()


@pytest_asyncio.fixture
async def fake_redis() -> AsyncIterator[FakeAsyncRedis]:
    """Create a fake Redis instance for testing."""
    redis = FakeAsyncRedis(decode_responses=True)
    yield redis
    await redis.aclose()


@pytest_asyncio.fixture
async def app(
    test_settings: Settings,
    db_session: AsyncSession,
    fake_redis: FakeAsyncRedis,
) -> AsyncIterator[FastAPI]:
    """Create a FastAPI app for testing with mocked dependencies."""

    # Override settings
    def override_get_settings() -> Settings:
        return test_settings

    # Override database session
    async def override_get_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    # Create app without lifespan for testing
    test_app = FastAPI(title="Eigentask API Test", description="Test API")

    # Add middleware
    test_app.add_middleware(
        SessionMiddleware,
        secret_key=test_settings.session_secret,
        same_site="lax",
        https_only=test_settings.cookie_secure,
    )

    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(test_settings.frontend_origin).removesuffix("/")],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Register routers
    test_app.include_router(auth_router.router)
    test_app.include_router(users_router.router)
    test_app.include_router(root_router.router)
    test_app.include_router(tasks_router.router)

    # Override dependencies
    test_app.dependency_overrides[get_settings] = override_get_settings
    test_app.dependency_overrides[get_session] = override_get_session

    # Attach fake Redis to app state
    test_app.state.redis = fake_redis

    yield test_app

    # Clear overrides
    test_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Create an async HTTP client for testing."""
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_oidc_discovery() -> Iterator[MagicMock]:
    """Mock OIDC discovery document."""
    discovery_doc = {
        "issuer": "https://keycloak.test/realms/test-realm",
        "authorization_endpoint": "https://keycloak.test/realms/test-realm/protocol/openid-connect/auth",
        "token_endpoint": "https://keycloak.test/realms/test-realm/protocol/openid-connect/token",
        "jwks_uri": "https://keycloak.test/realms/test-realm/protocol/openid-connect/certs",
        "userinfo_endpoint": "https://keycloak.test/realms/test-realm/protocol/openid-connect/userinfo",
        "end_session_endpoint": "https://keycloak.test/realms/test-realm/protocol/openid-connect/logout",
    }

    # Patch where it's used (router imports get_discovery_document at load time)
    with patch("app.routers.auth.get_discovery_document", new_callable=AsyncMock) as mock:
        mock.return_value = discovery_doc
        yield mock


@pytest.fixture
def mock_jwks() -> Iterator[MagicMock]:
    """Mock JWKS endpoint."""
    jwks = {
        "keys": [
            {
                "kid": "test-key-id",
                "kty": "RSA",
                "alg": "RS256",
                "use": "sig",
                "n": "test-n-value",
                "e": "AQAB",
            },
        ],
    }

    with patch("app.core.auth.get_jwks", new_callable=AsyncMock) as mock:
        mock.return_value = jwks
        yield mock


@pytest.fixture
def mock_verify_token() -> Iterator[MagicMock]:
    """Mock token verification to bypass actual JWT validation.

    Returns a mock that can be configured per-test to return different user payloads.
    """
    mock_payload = {
        "sub": "test-user-123",
        "preferred_username": "testuser",
        "email": "test@example.com",
        "name": "Test User",
        "realm_access": {"roles": ["user"]},
    }

    with patch("app.core.auth.verify_token", new_callable=AsyncMock) as mock:
        mock.return_value = mock_payload
        yield mock


@pytest.fixture
def authenticated_user() -> dict[str, Any]:
    """Return a default authenticated user payload."""
    return {
        "sub": "test-user-123",
        "preferred_username": "testuser",
        "email": "test@example.com",
        "name": "Test User",
        "roles": ["user"],
    }


@pytest.fixture
def another_user() -> dict[str, Any]:
    """Return another user payload for testing authorization."""
    return {
        "sub": "another-user-456",
        "preferred_username": "anotheruser",
        "email": "another@example.com",
        "name": "Another User",
        "roles": ["user"],
    }


@pytest_asyncio.fixture
async def authenticated_client(
    test_settings: Settings,
    db_session: AsyncSession,
    fake_redis: FakeAsyncRedis,
    authenticated_user: dict[str, Any],
) -> AsyncIterator[AsyncClient]:
    """Create an authenticated HTTP client for testing.

    This client bypasses OIDC and JWT verification by overriding the
    dependency directly.
    """
    # Import here to avoid circular dependencies
    from app.core.auth import get_current_user

    # Create app with mocked authentication
    def override_get_settings() -> Settings:
        return test_settings

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    def override_get_current_user() -> dict[str, Any]:
        return authenticated_user

    # Create app
    test_app = FastAPI(title="Eigentask API Test", description="Test API")

    test_app.add_middleware(
        SessionMiddleware,
        secret_key=test_settings.session_secret,
        same_site="lax",
        https_only=test_settings.cookie_secure,
    )

    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(test_settings.frontend_origin).removesuffix("/")],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    test_app.include_router(auth_router.router)
    test_app.include_router(users_router.router)
    test_app.include_router(root_router.router)
    test_app.include_router(tasks_router.router)

    # Override dependencies
    test_app.dependency_overrides[get_settings] = override_get_settings
    test_app.dependency_overrides[get_session] = override_get_session
    test_app.dependency_overrides[get_current_user] = override_get_current_user

    # Attach fake Redis
    test_app.state.redis = fake_redis

    transport = ASGITransport(app=test_app)  # type: ignore[arg-type]
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": "Bearer fake-test-token"},
    ) as ac:
        yield ac

    test_app.dependency_overrides.clear()

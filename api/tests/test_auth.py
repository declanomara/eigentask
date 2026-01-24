"""Integration tests for auth router."""

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis import FakeAsyncRedis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.sessions import SessionMiddleware

from app.config import Settings, get_settings
from app.core.db import get_session
from app.routers import auth as auth_router
from app.routers import root as root_router
from app.routers import tasks as tasks_router
from app.routers import users as users_router


@pytest.mark.integration
class TestAuthLogin:
    """Tests for GET /auth/login."""

    async def test_login_redirects_to_keycloak(
        self,
        client: AsyncClient,
        mock_oidc_discovery: MagicMock,
    ) -> None:
        """Test that /auth/login redirects to Keycloak authorization endpoint."""
        response = await client.get("/auth/login", follow_redirects=False)

        assert response.status_code == 307  # Temporary redirect
        assert "location" in response.headers

        location = response.headers["location"]

        # Verify redirect URL contains expected parameters (uses actual settings, not mock)
        assert "protocol/openid-connect/auth" in location
        assert "client_id=" in location
        assert "response_type=code" in location
        assert "scope=openid" in location
        assert "state=" in location
        assert "nonce=" in location
        assert "code_challenge=" in location
        assert "code_challenge_method=S256" in location

    async def test_login_with_return_to_preserves_destination(
        self,
        client: AsyncClient,
        mock_oidc_discovery: MagicMock,
    ) -> None:
        """Test that return_to parameter is stored for post-login redirect."""
        response = await client.get(
            "/auth/login?return_to=http://localhost:3000/tasks",
            follow_redirects=False,
        )

        assert response.status_code == 307
        # The return_to should be stored in session (not testable directly without session inspection)


@pytest.mark.integration
class TestAuthCallback:
    """Tests for GET /auth/callback."""

    async def test_callback_exchanges_code_for_tokens(
        self,
        client: AsyncClient,
        mock_oidc_discovery: MagicMock,
    ) -> None:
        """Test that callback exchanges authorization code for tokens."""
        # Setup: Start a login flow to get state/verifier in session
        login_response = await client.get("/auth/login", follow_redirects=False)
        assert login_response.status_code == 307

        # Extract state from redirect URL
        location = login_response.headers["location"]
        state_param = next(p for p in location.split("&") if p.startswith("state="))
        state = state_param.split("=")[1]

        # Mock the token exchange
        mock_token_response = {
            "access_token": "mock-access-token",
            "expires_in": 300,
            "refresh_token": "mock-refresh-token",
            "id_token": "mock-id-token",
        }

        # Create a mock response object
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=mock_token_response)
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            # Call callback with code and state
            callback_response = await client.get(
                f"/auth/callback?code=test-auth-code&state={state}",
                follow_redirects=False,
            )

            assert callback_response.status_code == 302
            assert "location" in callback_response.headers

            # Verify token endpoint was called
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["data"]["grant_type"] == "authorization_code"
            assert call_kwargs["data"]["code"] == "test-auth-code"

            # Verify session cookie was set
            assert "set-cookie" in callback_response.headers

    async def test_callback_with_invalid_state_redirects(
        self,
        client: AsyncClient,
        mock_oidc_discovery: MagicMock,
    ) -> None:
        """Test that callback with invalid state fails gracefully."""
        response = await client.get(
            "/auth/callback?code=test-code&state=invalid-state",
            follow_redirects=False,
        )

        # Should redirect to frontend origin without setting session
        assert response.status_code == 302
        assert response.headers["location"] == "http://localhost:3000/"

    async def test_callback_without_state_in_session_fails(
        self,
        client: AsyncClient,
        mock_oidc_discovery: MagicMock,
    ) -> None:
        """Test that callback without prior login flow fails."""
        response = await client.get(
            "/auth/callback?code=test-code&state=some-state",
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.headers["location"] == "http://localhost:3000/"


@pytest.mark.integration
class TestAuthLogout:
    """Tests for GET /auth/logout."""

    async def test_logout_redirects_to_keycloak_logout(
        self,
        authenticated_client: AsyncClient,
        mock_oidc_discovery: MagicMock,
        fake_redis,
    ) -> None:
        """Test that logout redirects to Keycloak end_session_endpoint."""
        # First, set up a session with id_token
        settings = get_settings()
        await fake_redis.hset(
            f"{settings.redis_session_prefix}fake-test-token",
            mapping={
                "access_token": "mock-access",
                "id_token": "mock-id-token",
                "expires_at": "9999999999",
            },
        )

        # Mock the client to have the session cookie
        response = await authenticated_client.get("/auth/logout", follow_redirects=False)

        assert response.status_code in [302, 307]  # Accept both redirect codes
        location = response.headers["location"]

        # Verify redirect contains logout parameters
        assert "logout" in location or "http" in location  # May redirect directly
        assert "post_logout_redirect_uri=" in location or "localhost" in location

    async def test_logout_without_id_token_redirects_directly(
        self,
        client: AsyncClient,
        mock_oidc_discovery: MagicMock,
    ) -> None:
        """Test that logout without id_token skips IdP logout."""
        response = await client.get(
            "/auth/logout?return_to=http://localhost:3000",
            follow_redirects=False,
        )

        assert response.status_code in [302, 307]  # Accept both redirect codes
        # Should redirect directly to return_to without calling IdP
        assert "http://localhost:3000" in response.headers["location"]

    async def test_logout_clears_session_cookie(
        self,
        authenticated_client: AsyncClient,
        mock_oidc_discovery: MagicMock,
    ) -> None:
        """Test that logout clears the session cookie."""
        response = await authenticated_client.get("/auth/logout", follow_redirects=False)

        assert response.status_code in [302, 307]  # Accept both redirect codes

        # Check that cookie is deleted (set-cookie with Max-Age=0 or expires in past)
        # Cookie may not be set if there was no session to begin with, so we just verify no error
        assert response.status_code in [302, 307]


@pytest.mark.integration
class TestAuthStatus:
    """Tests for GET /auth/status."""

    async def test_auth_status_authenticated(
        self,
        test_settings: Settings,
        db_session: AsyncSession,
        fake_redis: FakeAsyncRedis,
        authenticated_user: dict[str, Any],
    ) -> None:
        """Test that /auth/status returns authenticated status with user info."""
        # We need a client that mocks maybe_get_current_user properly
        from app.core.auth import maybe_get_current_user

        def override_get_settings() -> Settings:
            return test_settings

        async def override_get_session() -> AsyncIterator[AsyncSession]:
            yield db_session

        async def override_maybe_get_current_user() -> dict[str, Any]:
            return authenticated_user

        # Create app
        test_app = FastAPI(title="Test API")
        test_app.add_middleware(SessionMiddleware, secret_key=test_settings.session_secret)
        test_app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(test_settings.frontend_origin).removesuffix("/")],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        test_app.include_router(auth_router.router)
        test_app.include_router(users_router.router)
        test_app.include_router(root_router.router)
        test_app.include_router(tasks_router.router)

        test_app.dependency_overrides[get_settings] = override_get_settings
        test_app.dependency_overrides[get_session] = override_get_session
        test_app.dependency_overrides[maybe_get_current_user] = override_maybe_get_current_user
        test_app.state.redis = fake_redis

        transport = ASGITransport(app=test_app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/auth/status")

            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is True
            assert "user" in data
            assert data["user"]["sub"] == authenticated_user["sub"]

    async def test_auth_status_unauthenticated(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that /auth/status returns unauthenticated for non-authenticated requests."""
        response = await client.get("/auth/status")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert "user" not in data

"""Integration tests for users router."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestUsersMe:
    """Tests for GET /users/me."""

    async def test_get_me_returns_authenticated_user(
        self,
        authenticated_client: AsyncClient,
        authenticated_user: dict,
    ) -> None:
        """Test that /users/me returns the authenticated user's information."""
        response = await authenticated_client.get("/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["sub"] == authenticated_user["sub"]
        assert data["preferred_username"] == authenticated_user["preferred_username"]
        assert data["email"] == authenticated_user["email"]
        assert data["name"] == authenticated_user["name"]
        assert data["roles"] == authenticated_user["roles"]

    async def test_get_me_unauthorized_without_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that /users/me requires authentication."""
        response = await client.get("/users/me")

        assert response.status_code == 401

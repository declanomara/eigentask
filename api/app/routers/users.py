"""User routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_me(current_user: Annotated[dict[str, Any], Depends(get_current_user)]) -> dict[str, Any]:
    """Return the current authenticated user."""
    return current_user

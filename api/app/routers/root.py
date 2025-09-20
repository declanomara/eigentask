"""Root and health routes."""

from fastapi import APIRouter

router = APIRouter(tags=["root"])


@router.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Hello World"}


@router.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"message": "OK"}

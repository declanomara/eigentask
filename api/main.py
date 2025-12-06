from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis import asyncio as redis
from starlette.middleware.sessions import SessionMiddleware

import app.models
from app.config import get_settings
from app.core.db import Base, engine
from app.routers import auth as auth_router
from app.routers import root as root_router
from app.routers import tasks as tasks_router
from app.routers import users as users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Initialize shared state on startup and cleanup on shutdown."""
    # Initialize shared Redis client
    app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)
    # Create database tables if they do not exist (no Alembic yet)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield
    finally:
        # Close Redis client gracefully on shutdown
        await app.state.redis.aclose()


app = FastAPI(title="Eigentask API", description="API for Eigentask", lifespan=lifespan)

settings = get_settings()

# Minimal session support for PKCE/state
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=settings.cookie_secure,
)

# CORS for frontend dev server to call protected endpoints with credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(settings.frontend_origin).removesuffix("/")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Register API routers
app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(root_router.router)
app.include_router(tasks_router.router)

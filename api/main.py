
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.routers import auth as auth_router
from app.routers import root as root_router
from app.routers import users as users_router

app = FastAPI(title="Eigentask API", description="API for Eigentask")

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
    allow_origins=[str(settings.frontend_origin)],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Register API routers
app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(root_router.router)

from fastapi import FastAPI
from fastapi import Depends, Request
from typing import Any, TypedDict, NotRequired, cast
from app.auth import get_current_user, get_discovery_document
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from urllib.parse import urlencode
import os
import secrets
import hashlib
import base64
import httpx
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Eigentask API", description="API for Eigentask")

# Keycloak OAuth2 configuration
KEYCLOAK_URL: str = os.getenv("KEYCLOAK_URL", "https://eigentask.com/auth")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "eigentask")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "eigentask")
KEYCLOAK_CLIENT_SECRET: str | None = os.getenv("KEYCLOAK_CLIENT_SECRET")
SESSION_SECRET: str = os.getenv("SESSION_SECRET", "dev-insecure-session-secret")
COOKIE_DOMAIN: str | None = os.getenv("COOKIE_DOMAIN")
COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/callback")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

# Minimal session support for PKCE/state
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=COOKIE_SECURE,
)

# CORS for frontend dev server to call protected endpoints with credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class TokenResponse(TypedDict):
    access_token: str
    token_type: str
    expires_in: int
    id_token: NotRequired[str]
    refresh_token: NotRequired[str]
    scope: NotRequired[str]

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health():
    return {"message": "OK"}

@app.get("/protected")
async def protected_route(current_user: dict[str, Any] = Depends(get_current_user)):
    """Protected route that requires authentication"""
    return {"message": "Hello, authenticated user!", "user": current_user}

def _generate_pkce_pair() -> tuple[str, str]:
    verifier_bytes = secrets.token_urlsafe(64)
    verifier = verifier_bytes[:128]
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("utf-8")).digest()
    ).decode("utf-8").rstrip("=")
    return verifier, challenge


@app.get("/login")
async def login(request: Request):
    """Start OIDC Authorization Code + PKCE flow by redirecting to Keycloak."""
    discovery = await get_discovery_document()
    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)
    verifier, challenge = _generate_pkce_pair()

    # Store state, nonce, verifier in session
    request.session["oauth_state"] = state
    request.session["oauth_nonce"] = nonce
    request.session["pkce_verifier"] = verifier

    params = {
        "client_id": KEYCLOAK_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid profile email",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    redirect_url = f"{discovery['authorization_endpoint']}?{urlencode(params)}"
    return RedirectResponse(redirect_url)


@app.get("/callback")
async def oidc_callback(request: Request, code: str, state: str):
    """Handle the OIDC callback: verify state and exchange code for tokens."""
    saved_state = request.session.get("oauth_state")
    verifier = request.session.get("pkce_verifier")
    if not saved_state or not verifier or state != saved_state:
        return RedirectResponse("/", status_code=302)

    discovery = await get_discovery_document()

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": KEYCLOAK_CLIENT_ID,
        "code_verifier": verifier,
    }

    headers: dict[str, str] = {"Content-Type": "application/x-www-form-urlencoded"}
    auth: httpx.Auth | None = None
    if KEYCLOAK_CLIENT_SECRET:
        # Use client secret if configured
        auth = httpx.BasicAuth(KEYCLOAK_CLIENT_ID, KEYCLOAK_CLIENT_SECRET)
        data.pop("client_id", None)

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            discovery["token_endpoint"], data=data, headers=headers, auth=auth, timeout=15
        )
        token_resp.raise_for_status()
        tokens = cast(TokenResponse, token_resp.json())

    # Clear transient values from session
    for k in ("oauth_state", "oauth_nonce", "pkce_verifier"):
        request.session.pop(k, None)

    response = RedirectResponse(url="/protected", status_code=302)
    # Set HttpOnly cookie for API to read
    cookie_params = {
        "httponly": True,
        "secure": COOKIE_SECURE,
        "samesite": "lax",
        "path": "/",
    }
    if COOKIE_DOMAIN:
        cookie_params["domain"] = COOKIE_DOMAIN  # type: ignore[index]

    if "access_token" in tokens:
        response.set_cookie("access_token", tokens["access_token"], **cookie_params)
    if "refresh_token" in tokens:
        response.set_cookie("refresh_token", tokens["refresh_token"], **cookie_params)
    if "id_token" in tokens:
        response.set_cookie("id_token", cast(str, tokens["id_token"]), **cookie_params)

    return response


@app.get("/logout")
async def logout(request: Request):
    """Clear cookies and redirect to Keycloak end-session if available."""
    discovery = await get_discovery_document()
    id_token = request.cookies.get("id_token")
    post_logout_redirect_uri = os.getenv("POST_LOGOUT_REDIRECT_URI", "http://localhost:8000/")
    params = {"post_logout_redirect_uri": post_logout_redirect_uri}
    if id_token:
        params["id_token_hint"] = id_token

    end_session = discovery.get("end_session_endpoint") or f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/logout"
    redirect = f"{end_session}?{urlencode(params)}"
    response = RedirectResponse(url=redirect, status_code=302)
    # Remove cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    response.delete_cookie("id_token")
    return response

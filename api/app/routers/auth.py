"""Authentication routes."""

import secrets
from typing import TYPE_CHECKING, Annotated, Any, cast
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.core.auth import (
    _generate_pkce_pair,
    get_discovery_document,
    maybe_get_current_user,
)
from app.core.helpers import _sanitize_return_to
from app.core.session import (
    StoredTokens,
    delete_session,
    get_tokens,
    new_sid,
    set_tokens,
)

if TYPE_CHECKING:
    from app.core.types import TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

settings = get_settings()


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    """Start OIDC Authorization Code + PKCE flow by redirecting to Keycloak."""
    discovery = await get_discovery_document()
    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)
    verifier, challenge = _generate_pkce_pair()

    # Store state, nonce, verifier in session
    request.session["oauth_state"] = state
    request.session["oauth_nonce"] = nonce
    request.session["pkce_verifier"] = verifier

    # Store safe post-login redirect
    request.session["post_login_redirect"] = _sanitize_return_to(
        request.query_params.get("return_to", str(settings.frontend_origin)),
    )

    params = {
        "client_id": settings.keycloak_client_id,
        "redirect_uri": settings.callback_url,
        "response_type": "code",
        "scope": "openid profile email offline_access",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    redirect_url = f"{discovery['authorization_endpoint']}?{urlencode(params)}"
    return RedirectResponse(redirect_url)


@router.get("/callback")
async def oidc_callback(request: Request, code: str, state: str) -> RedirectResponse:
    """Handle the OIDC callback: verify state and exchange code for tokens."""
    saved_state = request.session.get("oauth_state")
    verifier = request.session.get("pkce_verifier")
    if not saved_state or not verifier or state != saved_state:
        return RedirectResponse(str(settings.frontend_origin), status_code=302)

    discovery = await get_discovery_document()

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.callback_url,
        "client_id": settings.keycloak_client_id,
        "code_verifier": verifier,
    }

    headers: dict[str, str] = {"Content-Type": "application/x-www-form-urlencoded"}
    auth: httpx.Auth | None = None

    if settings.keycloak_client_secret:
        # Use client secret if configured
        auth = httpx.BasicAuth(settings.keycloak_client_id, settings.keycloak_client_secret)
        data.pop("client_id", None)

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            discovery["token_endpoint"],
            data=data,
            headers=headers,
            auth=auth,
            timeout=15,
        )
        token_resp.raise_for_status()
        tokens = cast("TokenResponse", token_resp.json())

    # Clear transient values from session
    for k in ("oauth_state", "oauth_nonce", "pkce_verifier"):
        request.session.pop(k, None)
    # Determine where to send the user after login
    post_login_redirect = request.session.pop("post_login_redirect", None)
    redirect_target = _sanitize_return_to(post_login_redirect)

    # Create opaque session id and persist tokens server-side (Redis)
    response = RedirectResponse(url=redirect_target, status_code=302)
    token_bundle: StoredTokens = {
        "access_token": tokens["access_token"],
        "expires_at": int(__import__("time").time()) + int(tokens.get("expires_in", 300)),
    }
    if "refresh_token" in tokens:
        token_bundle["refresh_token"] = tokens["refresh_token"]  # type: ignore[typeddict-item]
    if "id_token" in tokens:
        token_bundle["id_token"] = tokens["id_token"]  # type: ignore[typeddict-item]

    sid = new_sid()
    r = request.app.state.redis
    await set_tokens(r, sid, token_bundle)

    # Set only the opaque session id as httpOnly cookie (persistent across browser restarts)
    cookie_params = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "path": "/",
        "max_age": settings.redis_session_ttl_seconds,
    }
    if settings.cookie_domain:
        cookie_params["domain"] = settings.cookie_domain
    response.set_cookie(settings.session_cookie_name, sid, **cookie_params)
    return response


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    """Clear cookies and redirect to Keycloak end-session if available."""
    discovery = await get_discovery_document()
    # Retrieve id_token from server-side session if available
    sid = request.cookies.get(settings.session_cookie_name)
    r = request.app.state.redis if sid else None
    stored = await get_tokens(r, sid) if r and sid else None
    id_token: str | None = stored.get("id_token") if stored else None  # type: ignore[assignment]
    post_logout_redirect_uri = request.query_params.get("return_to", str(settings.frontend_origin))

    # If we don't have an id_token, skip calling the IdP end-session endpoint.
    # Some providers (e.g., Keycloak) require id_token_hint and will error otherwise.
    if not id_token:
        response = RedirectResponse(url=post_logout_redirect_uri, status_code=302)
        # Clear server-side session and the sid cookie if present
        if sid:
            r = request.app.state.redis
            await delete_session(r, sid)
            response.delete_cookie(settings.session_cookie_name)
        return response

    params = {"post_logout_redirect_uri": post_logout_redirect_uri}
    params["id_token_hint"] = id_token

    end_session = discovery.get("end_session_endpoint")
    if not end_session:
        keycloak_base = str(settings.keycloak_url).removesuffix("/")
        end_session = f"{keycloak_base}/realms/{settings.keycloak_realm}/protocol/openid-connect/logout"
    redirect = f"{end_session}?{urlencode(params)}"
    response = RedirectResponse(url=redirect, status_code=302)
    # Remove server-side session and sid cookie
    if sid:
        r = request.app.state.redis
        await delete_session(r, sid)
        response.delete_cookie(settings.session_cookie_name)
    return response


@router.get("/status")
async def auth_status(
    user: Annotated[dict[str, Any] | None, Depends(maybe_get_current_user)],
) -> dict[str, object]:
    """Return authentication status without raising 401 errors.

    If authenticated, includes a `user` object matching `/users/me`.
    """
    if user is None:
        return {"authenticated": False}
    return {"authenticated": True, "user": user}

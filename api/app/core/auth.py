import base64
import hashlib
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, NotRequired, TypedDict, cast

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.core.session import get_tokens, is_expired, set_tokens
from app.core.types import RefreshResult

settings = get_settings()


class OIDCDiscoveryDocument(TypedDict):
    """OIDC discovery document."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    userinfo_endpoint: NotRequired[str]
    end_session_endpoint: NotRequired[str]


class JWK(TypedDict):
    """JWK."""

    kid: str
    kty: str
    alg: str
    use: str
    n: NotRequired[str]
    e: NotRequired[str]


class JWKS(TypedDict):
    """JWKS."""

    keys: list[JWK]


class TTLCache[T]:
    """Simple in-memory TTL cache for a single value."""

    def __init__(self) -> None:
        """Initialize the cache with no value and no expiry."""
        self.value: T | None = None
        self.expiry: datetime | None = None

    def get(self) -> T | None:
        """Return the cached value if not expired; otherwise return None."""
        if self.value is not None and self.expiry and datetime.now(tz=UTC) < self.expiry:
            return self.value
        return None

    def set(self, value: T, ttl: timedelta) -> None:
        """Set a value in the cache with a time-to-live (TTL)."""
        self.value = value
        self.expiry = datetime.now(tz=UTC) + ttl


_discovery_cache: TTLCache[OIDCDiscoveryDocument] = TTLCache()
_jwks_cache: TTLCache[JWKS] = TTLCache()

security = HTTPBearer(auto_error=False)
settings = get_settings()


async def get_discovery_document() -> OIDCDiscoveryDocument:
    """Fetch and cache the realm OIDC discovery document."""
    cached = _discovery_cache.get()
    if cached is not None:
        return cast("OIDCDiscoveryDocument", cached)

    keycloak_base = str(settings.keycloak_url).removesuffix("/")
    url = f"{keycloak_base}/realms/{settings.keycloak_realm}/.well-known/openid-configuration"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = cast("OIDCDiscoveryDocument", resp.json())
            _discovery_cache.set(data, ttl=timedelta(hours=1))
            return data
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to fetch discovery document: {exc}",
        ) from exc


async def get_jwks() -> JWKS:
    """Fetch and cache JWKS for verifying tokens."""
    cached = _jwks_cache.get()
    if cached is not None:
        return cast("JWKS", cached)

    discovery = await get_discovery_document()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(discovery["jwks_uri"], timeout=10)
            resp.raise_for_status()
            data = cast("JWKS", resp.json())
            _jwks_cache.set(data, ttl=timedelta(hours=1))
            return data
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to fetch JWKS: {exc}",
        ) from exc


def get_public_key(token: str, keys: JWKS) -> str:
    """Extract the correct public key for the token."""
    # Decode token header to get key ID
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    if not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing key ID",
        )

    # Find the correct public key
    for key in keys.get("keys", []):
        if key.get("kid") == kid:
            # Extract RSA components
            def _b64url_to_bytes(value: str) -> bytes:
                padding = "=" * (-len(value) % 4)
                return base64.urlsafe_b64decode(value + padding)

            n = _b64url_to_bytes(key["n"])  # type: ignore[arg-type]
            e = _b64url_to_bytes(key["e"])  # type: ignore[arg-type]

            # Convert to integers
            n_int = int.from_bytes(n, "big")
            e_int = int.from_bytes(e, "big")

            # Create RSA public key
            public_key = rsa.RSAPublicNumbers(e_int, n_int).public_key()

            # Convert to PEM format
            pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )

            return pem.decode("utf-8")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to find appropriate key",
    )


def _get_bearer_token(credentials: HTTPAuthorizationCredentials | None) -> str | None:
    """Return bearer token from Authorization header, if present."""
    if credentials and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    return None


async def _get_session_access_token(request: Request) -> str | None:
    """Retrieve an access token from the Redis-backed session, refreshing if needed.

    Returns the access token string if available and valid; otherwise None.
    """
    sid = request.cookies.get(settings.session_cookie_name)
    if not sid:
        return None

    r = request.app.state.redis
    stored = await get_tokens(r, sid)
    if not stored:
        return None

    if is_expired(stored):
        refreshed = await refresh_tokens_via_oidc(stored.get("refresh_token", ""))
        if not refreshed:
            return None
        await set_tokens(r, sid, refreshed)
        return refreshed.get("access_token")

    return stored.get("access_token")


async def verify_token(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ],
) -> dict[str, Any]:
    """Verify JWT token using Authorization header or Redis-backed session."""
    token = _get_bearer_token(credentials) or await _get_session_access_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    try:
        jwks = await get_jwks()
        public_key_pem = get_public_key(token, jwks)
        discovery = await get_discovery_document()
        payload = jwt.decode(
            token,
            public_key_pem,
            algorithms=["RS256"],
            audience=settings.keycloak_client_id,
            issuer=discovery["issuer"],
            options={"verify_exp": True, "verify_aud": True, "verify_iss": True},
        )
        return cast("dict[str, Any]", payload)
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        ) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e!s}",
        ) from e


def get_current_user(
    payload: Annotated[
        dict[str, Any],
        Depends(verify_token),
    ],
) -> dict[str, Any]:
    """Extract user information from verified token."""
    return {
        "sub": payload.get("sub"),
        "preferred_username": payload.get("preferred_username"),
        "email": payload.get("email"),
        "name": payload.get("name"),
        "roles": payload.get("realm_access", {}).get("roles", []),
    }


def _generate_pkce_pair() -> tuple[str, str]:
    verifier_bytes = secrets.token_urlsafe(64)
    verifier = verifier_bytes[:128]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest()).decode("utf-8").rstrip("=")
    return verifier, challenge


async def maybe_get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ],
) -> dict[str, Any] | None:
    """Best-effort dependency that returns the user or None if unauthenticated.

    Swallows only 401 Unauthorized to enable non-erroring auth checks (e.g., /auth/status).
    Other HTTPExceptions are re-raised.
    """
    try:
        payload = await verify_token(request, credentials)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return None
        raise
    return get_current_user(payload)


async def refresh_tokens_via_oidc(refresh_token: str) -> RefreshResult | None:
    """Refresh access (and possibly refresh/id) tokens via the OIDC token endpoint.

    Returns a new token bundle on success, or None on failure.
    """
    if not refresh_token:
        return None

    discovery = await get_discovery_document()

    data: dict[str, str] = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": settings.keycloak_client_id,
    }
    auth: httpx.Auth | None = None
    if settings.keycloak_client_secret:
        auth = httpx.BasicAuth(settings.keycloak_client_id, settings.keycloak_client_secret)
        data.pop("client_id", None)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            discovery["token_endpoint"],
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=auth,
            timeout=15,
        )

    if resp.status_code != httpx.codes.OK:
        return None

    payload = resp.json()
    result: RefreshResult = {
        "access_token": payload["access_token"],
        "expires_at": int(time.time()) + int(payload.get("expires_in", 300)),
    }
    if "refresh_token" in payload:
        result["refresh_token"] = payload["refresh_token"]
    if "id_token" in payload:
        result["id_token"] = payload["id_token"]
    return result

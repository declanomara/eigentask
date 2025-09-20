from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import httpx
import os
from datetime import datetime, timedelta
from typing import Any, TypedDict, NotRequired, cast

# Keycloak configuration
KEYCLOAK_URL: str = os.getenv("KEYCLOAK_URL", "https://eigentask.com/auth")
KEYCLOAK_REALM: str = os.getenv("KEYCLOAK_REALM", "eigentask")
KEYCLOAK_CLIENT_ID: str = os.getenv("KEYCLOAK_CLIENT_ID", "eigentask")


class OIDCDiscoveryDocument(TypedDict):
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    userinfo_endpoint: NotRequired[str]
    end_session_endpoint: NotRequired[str]


class JWK(TypedDict):
    kid: str
    kty: str
    alg: str
    use: str
    n: NotRequired[str]
    e: NotRequired[str]


class JWKS(TypedDict):
    keys: list[JWK]


_discovery_cache: OIDCDiscoveryDocument | None = None
_discovery_cache_expiry: datetime | None = None
_jwks_cache: JWKS | None = None
_jwks_cache_expiry: datetime | None = None

security = HTTPBearer(auto_error=False)


async def get_discovery_document() -> OIDCDiscoveryDocument:
    """Fetch and cache the realm OIDC discovery document."""
    global _discovery_cache, _discovery_cache_expiry
    if (
        _discovery_cache
        and _discovery_cache_expiry
        and datetime.now() < _discovery_cache_expiry
    ):
        return _discovery_cache

    url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/.well-known/openid-configuration"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = cast(OIDCDiscoveryDocument, resp.json())
            _discovery_cache = data
            _discovery_cache_expiry = datetime.now() + timedelta(hours=1)
            return data
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to fetch OIDC discovery document: {exc}",
        )


async def get_jwks() -> JWKS:
    """Fetch and cache JWKS for verifying tokens."""
    global _jwks_cache, _jwks_cache_expiry
    if _jwks_cache and _jwks_cache_expiry and datetime.now() < _jwks_cache_expiry:
        return _jwks_cache

    discovery = await get_discovery_document()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(discovery["jwks_uri"], timeout=10)
            resp.raise_for_status()
            data = cast(JWKS, resp.json())
            _jwks_cache = data
            _jwks_cache_expiry = datetime.now() + timedelta(hours=1)
            return data
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to fetch JWKS: {exc}",
        )


def get_public_key(token: str, keys: JWKS) -> str:
    """Extract the correct public key for the token"""
    try:
        # Decode token header to get key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing key ID"
            )

        # Find the correct public key
        for key in keys.get("keys", []):
            if key.get("kid") == kid:
                # Convert JWK to PEM format
                from cryptography.hazmat.primitives import serialization
                from cryptography.hazmat.primitives.asymmetric import rsa
                import base64

                # Extract RSA components
                def _b64url_to_bytes(value: str) -> bytes:
                    padding = "=" * (-len(value) % 4)
                    return base64.urlsafe_b64decode(value + padding)

                n = _b64url_to_bytes(cast(str, key["n"]))
                e = _b64url_to_bytes(cast(str, key["e"]))

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

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Error processing token: {str(e)}",
        )


async def verify_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    """Verify JWT token from Keycloak from Authorization header or access_token cookie."""
    token: str | None = None
    if credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token"
        )

    try:
        jwks = await get_jwks()
        public_key_pem = get_public_key(token, jwks)
        discovery = await get_discovery_document()
        payload = jwt.decode(
            token,
            public_key_pem,
            algorithms=["RS256"],
            audience=KEYCLOAK_CLIENT_ID,
            issuer=discovery["issuer"],
            options={"verify_exp": True, "verify_aud": True, "verify_iss": True},
        )
        return cast(dict[str, Any], payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        # Decode claims without verification to help diagnose audience/issuer mismatches
        unverified: dict[str, Any] | None
        try:
            unverified = cast(
                dict[str, Any],
                jwt.decode(
                    token,
                    options={
                        "verify_signature": False,
                        "verify_aud": False,
                        "verify_exp": False,
                        "verify_iss": False,
                    },
                ),
            )
        except Exception:
            unverified = None

        aud = unverified.get("aud") if isinstance(unverified, dict) else None
        azp = unverified.get("azp") if isinstance(unverified, dict) else None
        iss = unverified.get("iss") if isinstance(unverified, dict) else None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)} | token_aud={aud} expected_aud={KEYCLOAK_CLIENT_ID} azp={azp} iss={iss}",
        )


def get_current_user(payload: dict[str, Any] = Depends(verify_token)) -> dict[str, Any]:
    """Extract user information from verified token"""
    return {
        "sub": payload.get("sub"),
        "preferred_username": payload.get("preferred_username"),
        "email": payload.get("email"),
        "name": payload.get("name"),
        "roles": payload.get("realm_access", {}).get("roles", []),
    }

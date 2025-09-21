import json
import secrets
import time
from typing import TypedDict, cast

from redis import asyncio as redis

from app.config import get_settings


class StoredTokens(TypedDict, total=False):
    """Tokens stored in Redis."""

    access_token: str
    refresh_token: str
    id_token: str
    expires_at: int  # epoch seconds


_settings = get_settings()


def new_sid() -> str:
    """Generate a new session ID."""
    return secrets.token_urlsafe(32)


async def set_tokens(r: redis.Redis, sid: str, tokens: StoredTokens) -> None:
    """Set tokens in Redis."""
    await r.setex(_settings.redis_session_prefix + sid, _settings.redis_session_ttl_seconds, json.dumps(tokens))


async def get_tokens(r: redis.Redis, sid: str) -> StoredTokens | None:
    """Get tokens from Redis."""
    raw = await r.get(_settings.redis_session_prefix + sid)
    if not raw:
        return None
    try:
        data = cast("StoredTokens", json.loads(raw))
    except json.JSONDecodeError:
        return None
    return data


async def delete_session(r: redis.Redis, sid: str) -> None:
    """Delete a session from Redis."""
    await r.delete(_settings.redis_session_prefix + sid)


def is_expired(tokens: StoredTokens, skew: int = 60) -> bool:
    """Check if tokens have expired."""
    exp = tokens.get("expires_at")
    if exp is None:
        return True
    return int(time.time()) >= int(exp) - skew

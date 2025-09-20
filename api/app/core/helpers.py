from urllib.parse import urlparse

from app.config import get_settings

settings = get_settings()


def _sanitize_return_to(return_to: str | None) -> str:
    """Ensure the post-login redirect is safe.

    Allowed values:
    - Absolute URL whose origin matches FRONTEND_ORIGIN
    - A path beginning with '/'

    Anything else will fall back to FRONTEND_ORIGIN.
    """
    default = str(settings.frontend_origin)
    if not return_to:
        return default

    parsed = urlparse(return_to)
    fe = urlparse(str(settings.frontend_origin))
    # Relative path
    if not parsed.scheme and not parsed.netloc and return_to.startswith("/"):
        return f"{fe.scheme}://{fe.netloc}{return_to}"
    # Absolute URL with same origin
    if parsed.scheme and parsed.netloc and (parsed.scheme, parsed.netloc) == (fe.scheme, fe.netloc):
        # Rebuild full URL to normalize
        return (
            f"{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}"
            + (f"?{parsed.query}" if parsed.query else "")
            + (f"#{parsed.fragment}" if parsed.fragment else "")
        )

    return default

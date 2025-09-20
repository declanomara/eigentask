from typing import NotRequired, TypedDict


class TokenResponse(TypedDict):
    """Response from OIDC token endpoint."""

    access_token: str
    token_type: str
    expires_in: int
    id_token: NotRequired[str]
    refresh_token: NotRequired[str]
    scope: NotRequired[str]

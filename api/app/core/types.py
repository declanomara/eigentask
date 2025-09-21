from typing import NotRequired, TypedDict


class TokenResponse(TypedDict):
    """Response from OIDC token endpoint."""

    access_token: str
    token_type: str
    expires_in: int
    id_token: NotRequired[str]
    refresh_token: NotRequired[str]
    scope: NotRequired[str]


class RefreshResult(TypedDict, total=False):
    """Result of an OIDC refresh operation."""

    access_token: str
    refresh_token: NotRequired[str]
    id_token: NotRequired[str]
    expires_at: int

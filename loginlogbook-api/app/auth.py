"""Token-based authentication dependencies."""
import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings


def require_admin(
    settings: Annotated[Settings, Depends(get_settings)],
    x_admin_token: Annotated[str | None, Header()] = None,
) -> None:
    """Allow the request only if the admin token header matches."""
    if not x_admin_token or not secrets.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin token"
        )


def require_client(
    settings: Annotated[Settings, Depends(get_settings)],
    x_client_token: Annotated[str | None, Header()] = None,
) -> None:
    """Allow the request only if the client token header matches."""
    if not x_client_token or not secrets.compare_digest(x_client_token, settings.client_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid client token"
        )

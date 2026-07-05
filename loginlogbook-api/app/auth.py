"""Token-based authentication dependencies."""
import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.client_store import ClientStore
from app.config import Settings, get_settings


def get_client_store(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ClientStore:
    return ClientStore(settings.clients_file)


def require_admin(
    settings: Annotated[Settings, Depends(get_settings)],
    x_admin_token: Annotated[str | None, Header()] = None,
) -> None:
    if not x_admin_token or not secrets.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin token"
        )


def require_client(
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[ClientStore, Depends(get_client_store)],
    x_client_token: Annotated[str | None, Header()] = None,
) -> None:
    tokens = [t for t in settings.effective_client_tokens() + store.tokens() if t]
    candidate = x_client_token or ""
    valid = False
    for t in tokens:
        if secrets.compare_digest(candidate, t):
            valid = True
    if not x_client_token or not valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid client token"
        )

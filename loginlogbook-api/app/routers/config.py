"""Per-client configuration endpoint."""
from typing import Annotated

from fastapi import APIRouter, Depends, Header

from app.auth import require_client
from app.client_store import ClientStore
from app.models import ClientConfig
from app.routers.clients import get_client_store

router = APIRouter(tags=["config"])


@router.get("/config", dependencies=[Depends(require_client)])
def get_config(
    store: Annotated[ClientStore, Depends(get_client_store)],
    x_client_token: Annotated[str | None, Header()] = None,
) -> ClientConfig:
    record = store.find_by_token(x_client_token or "")
    allow_free_text = record.get("allow_free_text", True) if record else True
    return ClientConfig(allow_free_text=allow_free_text)

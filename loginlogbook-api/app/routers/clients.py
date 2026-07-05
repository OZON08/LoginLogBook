"""Client credential management endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_admin
from app.client_store import ClientStore
from app.models import ClientIn, ClientOut

router = APIRouter(prefix="/clients", tags=["clients"])


def get_client_store() -> ClientStore:
    """Overridden in app.main with a settings-backed provider."""
    raise NotImplementedError


@router.get("", dependencies=[Depends(require_admin)])
def list_clients(
    store: Annotated[ClientStore, Depends(get_client_store)],
) -> list[ClientOut]:
    return [ClientOut(name=n) for n in store.list_names()]


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def register_client(
    payload: ClientIn,
    store: Annotated[ClientStore, Depends(get_client_store)],
) -> ClientOut:
    try:
        store.add(payload.name, payload.token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ClientOut(name=payload.name)


@router.delete(
    "/{name}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def revoke_client(
    name: str,
    store: Annotated[ClientStore, Depends(get_client_store)],
) -> None:
    if not store.remove(name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown client")

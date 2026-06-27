"""Reasons CRUD endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_admin, require_client
from app.models import Reason, ReasonIn
from app.reasons_store import ReasonsStore

router = APIRouter(prefix="/reasons", tags=["reasons"])


def get_reasons_store() -> ReasonsStore:
    """Overridden in app.main with a settings-backed provider."""
    raise NotImplementedError


@router.get("", dependencies=[Depends(require_client)])
def list_reasons(
    store: Annotated[ReasonsStore, Depends(get_reasons_store)],
) -> list[Reason]:
    return store.list_active()


@router.post(
    "", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)]
)
def create_reason(
    payload: ReasonIn,
    store: Annotated[ReasonsStore, Depends(get_reasons_store)],
) -> Reason:
    return store.add(payload.label)


@router.delete(
    "/{reason_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_reason(
    reason_id: str,
    store: Annotated[ReasonsStore, Depends(get_reasons_store)],
) -> None:
    if not store.deactivate(reason_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown reason")

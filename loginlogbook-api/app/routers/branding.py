"""Branding logo distribution endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status

from app.auth import require_admin, require_client
from app.logo_store import LogoStore

router = APIRouter(prefix="/branding", tags=["branding"])


def get_logo_store() -> LogoStore:
    """Overridden in app.main with a settings-backed provider."""
    raise NotImplementedError


@router.get("/logo", dependencies=[Depends(require_client)])
def get_logo(store: Annotated[LogoStore, Depends(get_logo_store)]) -> Response:
    loaded = store.load()
    if loaded is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No logo set")
    content, content_type = loaded
    return Response(content=content, media_type=content_type)


@router.put(
    "/logo",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def put_logo(
    file: UploadFile,
    store: Annotated[LogoStore, Depends(get_logo_store)],
) -> None:
    content = await file.read()
    try:
        store.save(content, file.content_type or "")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

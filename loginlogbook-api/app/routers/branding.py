"""Branding logo distribution endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status

from app.auth import require_admin, require_client
from app.branding_store import BrandingStore
from app.logo_store import LogoStore
from app.models import BrandingConfig

router = APIRouter(prefix="/branding", tags=["branding"])


def get_logo_store() -> LogoStore:
    """Overridden in app.main with a settings-backed provider."""
    raise NotImplementedError


def get_branding_store() -> BrandingStore:
    """Overridden in app.main with a settings-backed provider."""
    raise NotImplementedError


@router.get("/logo", dependencies=[Depends(require_client)])
def get_logo(store: Annotated[LogoStore, Depends(get_logo_store)]) -> Response:
    loaded = store.load()
    if loaded is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No logo set")
    content, content_type = loaded
    headers = {}
    if content_type == "image/svg+xml":
        headers["Content-Disposition"] = "attachment; filename=\"logo.svg\""
    return Response(content=content, media_type=content_type, headers=headers)


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


@router.get("/config", dependencies=[Depends(require_client)])
def get_branding_config(
    store: Annotated[BrandingStore, Depends(get_branding_store)],
) -> BrandingConfig:
    return BrandingConfig(**store.load())


@router.put(
    "/config",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def put_branding_config(
    cfg: BrandingConfig,
    store: Annotated[BrandingStore, Depends(get_branding_store)],
) -> None:
    store.save(cfg.model_dump())

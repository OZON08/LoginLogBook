"""Global settings (language) and admin-UI locale distribution."""
import json
import re
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.auth import require_admin
from app.i18n import Translator
from app.models import LanguageSetting
from app.settings_store import SettingsStore

router = APIRouter(tags=["settings"])

_CODE_RE = re.compile(r"^[a-z]{2}$")
_ADMIN_LOCALES = Path(__file__).parent.parent / "locales" / "admin"


def get_settings_store() -> SettingsStore:
    """Overridden in app.main with a settings-backed provider."""
    raise NotImplementedError


def get_admin_translator() -> Translator:
    """Overridden in app.main with a settings-backed provider."""
    raise NotImplementedError


@router.get("/settings")
def get_app_settings(
    store: Annotated[SettingsStore, Depends(get_settings_store)],
    translator: Annotated[Translator, Depends(get_admin_translator)],
) -> dict:
    return {"language": store.load()["language"], "available": translator.available()}


@router.put(
    "/settings",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def put_app_settings(
    setting: LanguageSetting,
    store: Annotated[SettingsStore, Depends(get_settings_store)],
    translator: Annotated[Translator, Depends(get_admin_translator)],
) -> None:
    if setting.language not in translator.available():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Unknown language code")
    store.save({"language": setting.language})


@router.get("/locales/admin/{code}.json")
def get_admin_locale(code: str) -> Response:
    if not _CODE_RE.match(code):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    path = _ADMIN_LOCALES / f"{code}.json"
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return Response(content=path.read_text(encoding="utf-8"),
                    media_type="application/json")

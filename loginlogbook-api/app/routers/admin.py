"""Admin UI — serves the single-page client management interface."""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_HTML = (Path(__file__).parent.parent / "static" / "admin.html").read_text(encoding="utf-8")

_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'"
)


@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
def admin_page() -> HTMLResponse:
    return HTMLResponse(content=_HTML, headers={"Content-Security-Policy": _CSP})

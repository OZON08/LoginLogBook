"""Custom, localized HTML error pages returned to browser clients."""
import base64
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.i18n import Translator
from app.settings_store import SettingsStore

_LOCALES_DIR = Path(__file__).parent / "locales" / "api"
_LOGO_PATH = Path(__file__).parent / "static" / "loginlogbook-logo.svg"
_KNOWN_CODES = (403, 404, 405, 422, 500)
_translator = Translator(_LOCALES_DIR)


def _logo_data_uri() -> str:
    if not _LOGO_PATH.exists():
        return ""
    b64 = base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


_LOGO = _logo_data_uri()


def _wants_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "")


def _active_language(request: Request) -> str:
    try:
        settings_getter = request.app.dependency_overrides.get(get_settings, get_settings)
        return SettingsStore(settings_getter().settings_file).load()["language"]
    except Exception:
        return "de"


def _texts(code: int, lang: str) -> tuple[str, str]:
    key = str(code) if code in _KNOWN_CODES else "generic"
    return (
        _translator.t(f"error.page.{key}.title", lang),
        _translator.t(f"error.page.{key}.msg", lang),
    )


def _page(code: int, lang: str) -> str:
    title, message = _texts(code, lang)
    back = _translator.t("error.page.back", lang)
    logo = f'<img class="logo" src="{_LOGO}" alt="LoginLogBook">' if _LOGO else ""
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{code} – LoginLogBook</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: #0F172A;
  font-family: "Segoe UI", system-ui, sans-serif;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}}
.card {{
  background: #fff;
  border-radius: 12px;
  padding: 2.5rem 2rem;
  width: 100%;
  max-width: 480px;
  box-shadow: 0 24px 64px rgba(0,0,0,0.4);
  text-align: center;
}}
.logo {{ height: 96px; margin-bottom: 1.25rem; }}
.code {{ font-size: 4.5rem; font-weight: 800; color: #0F172A; line-height: 1; margin-bottom: 0.75rem; }}
h1 {{ font-size: 1.25rem; font-weight: 700; color: #0F172A; margin-bottom: 0.75rem; }}
p {{ font-size: 0.9375rem; color: #475569; margin-bottom: 1.75rem; line-height: 1.6; }}
a {{ display: inline-block; background: #2563EB; color: #fff; text-decoration: none;
     font-weight: 600; font-size: 0.9375rem; padding: 0.625rem 1.5rem; border-radius: 8px; }}
a:hover {{ background: #1D4ED8; }}
</style>
</head>
<body>
<div class="card">
  {logo}
  <div class="code">{code}</div>
  <h1>{title}</h1>
  <p>{message}</p>
  <a href="#" onclick="history.back();return false;">{back}</a>
</div>
</body>
</html>"""


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> HTMLResponse | JSONResponse:
        if not _wants_html(request):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        return HTMLResponse(content=_page(exc.status_code, _active_language(request)), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> HTMLResponse | JSONResponse:
        if not _wants_html(request):
            return JSONResponse(status_code=422, content={"detail": exc.errors()})
        return HTMLResponse(content=_page(422, _active_language(request)), status_code=422)

    @app.exception_handler(Exception)
    async def server_error(request: Request, exc: Exception) -> HTMLResponse | JSONResponse:
        if not _wants_html(request):
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})
        return HTMLResponse(content=_page(500, _active_language(request)), status_code=500)

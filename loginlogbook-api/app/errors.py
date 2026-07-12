"""Custom HTML error pages returned to browser clients."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

_DESCRIPTIONS: dict[int, tuple[str, str]] = {
    403: ("Zugriff verweigert", "Das angegebene Token ist ungültig oder fehlt."),
    404: ("Seite nicht gefunden", "Die angeforderte Ressource existiert nicht."),
    405: ("Methode nicht erlaubt", "Diese HTTP-Methode wird hier nicht unterstützt."),
    422: ("Ungültige Anfrage", "Die Anfrage enthält ungültige oder fehlende Felder."),
    500: ("Interner Fehler", "Ein unerwarteter Fehler ist aufgetreten. Bitte später erneut versuchen."),
}


def _wants_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "")


def _page(code: int, title: str, message: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="de">
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
.code {{
  font-size: 4rem;
  font-weight: 800;
  color: #E2E8F0;
  line-height: 1;
  margin-bottom: 0.75rem;
}}
h1 {{
  font-size: 1.25rem;
  font-weight: 700;
  color: #0F172A;
  margin-bottom: 0.75rem;
}}
p {{
  font-size: 0.9375rem;
  color: #475569;
  margin-bottom: 1.75rem;
  line-height: 1.6;
}}
a {{
  display: inline-block;
  background: #2563EB;
  color: #fff;
  text-decoration: none;
  font-weight: 600;
  font-size: 0.9375rem;
  padding: 0.625rem 1.5rem;
  border-radius: 8px;
}}
a:hover {{ background: #1D4ED8; }}
</style>
</head>
<body>
<div class="card">
  <div class="code">{code}</div>
  <h1>{title}</h1>
  <p>{message}</p>
  <a href="/admin">← Zur Übersicht</a>
</div>
</body>
</html>"""


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> HTMLResponse | JSONResponse:
        if not _wants_html(request):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        code = exc.status_code
        title, message = _DESCRIPTIONS.get(code, ("Fehler", str(exc.detail)))
        return HTMLResponse(content=_page(code, title, message), status_code=code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> HTMLResponse | JSONResponse:
        if not _wants_html(request):
            return JSONResponse(status_code=422, content={"detail": exc.errors()})
        title, message = _DESCRIPTIONS[422]
        return HTMLResponse(content=_page(422, title, message), status_code=422)

    @app.exception_handler(Exception)
    async def server_error(request: Request, exc: Exception) -> HTMLResponse | JSONResponse:
        if not _wants_html(request):
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})
        title, message = _DESCRIPTIONS[500]
        return HTMLResponse(content=_page(500, title, message), status_code=500)

"""FastAPI application factory and wiring."""
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import Settings, get_settings
from app.influx import InfluxGateway
from app.logo_store import LogoStore
from app.reasons_store import ReasonsStore
from app.routers import branding, events, health, reasons


def _rate_key(request: Request) -> str:
    """Rate-limit key: real client IP (X-Real-IP set by nginx, else direct host)."""
    return (
        request.headers.get("x-real-ip")
        or (request.client.host if request.client else "unknown")
    )


class _RateLimiter(BaseHTTPMiddleware):
    """60 requests per 60-second sliding window per rate key."""

    _LIMIT = 60
    _WINDOW = 60.0
    _MAX_KEYS = 10_000

    def __init__(self, app) -> None:
        super().__init__(app)
        self._hits: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next) -> Response:
        key = _rate_key(request)
        now = time.monotonic()
        recent = [t for t in self._hits.get(key, []) if now - t < self._WINDOW]
        if len(recent) >= self._LIMIT:
            return JSONResponse({"detail": "Too Many Requests"}, status_code=429)
        recent.append(now)
        self._hits[key] = recent
        if len(self._hits) > self._MAX_KEYS:
            expired = [k for k, ts in self._hits.items() if not ts or now - ts[-1] >= self._WINDOW]
            for k in expired:
                del self._hits[k]
        return await call_next(request)


def get_reasons_store() -> ReasonsStore:
    return ReasonsStore(get_settings().reasons_file)


def get_influx_gateway() -> InfluxGateway:
    return InfluxGateway(get_settings())


def get_logo_store() -> LogoStore:
    settings = get_settings()
    return LogoStore(settings.logo_dir, settings.logo_max_bytes)


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="LoginLogBook API", version="0.1.0")
    app.add_middleware(_RateLimiter)
    app.include_router(health.router)
    app.include_router(reasons.router)
    app.include_router(events.router)
    app.include_router(branding.router)
    app.dependency_overrides[reasons.get_reasons_store] = get_reasons_store
    app.dependency_overrides[events.get_influx_gateway] = get_influx_gateway
    app.dependency_overrides[branding.get_logo_store] = get_logo_store
    app.dependency_overrides[health.get_influx_gateway] = get_influx_gateway
    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: settings
    return app


app = create_app()

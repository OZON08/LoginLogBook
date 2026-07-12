"""FastAPI application factory and wiring."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.client_store import ClientStore
from app.errors import register_error_handlers
from app.config import Settings, get_settings
from app.influx import InfluxGateway
from app.logo_store import LogoStore
from app.reasons_store import ReasonsStore
from app.routers import branding, events, health, reasons
from app.routers import admin as admin_router
from app.routers import clients as clients_router
from app.routers import config as config_router

_STATIC_DIR = Path(__file__).parent / "static"
_DEFAULT_LOGO = _STATIC_DIR / "loginlogbook-logo.svg"


def get_reasons_store() -> ReasonsStore:
    return ReasonsStore(get_settings().reasons_file)


def get_influx_gateway() -> InfluxGateway:
    return InfluxGateway(get_settings())


def get_logo_store() -> LogoStore:
    settings = get_settings()
    return LogoStore(settings.logo_dir, settings.logo_max_bytes)


def get_client_store() -> ClientStore:
    return ClientStore(get_settings().clients_file)


def create_app(settings: Settings | None = None) -> FastAPI:
    _settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings is None and _DEFAULT_LOGO.exists():
            store = LogoStore(_settings.logo_dir, _settings.logo_max_bytes)
            if store.load() is None:
                store.save(_DEFAULT_LOGO.read_bytes(), "image/svg+xml")
        yield

    app = FastAPI(title="LoginLogBook API", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(reasons.router)
    app.include_router(events.router)
    app.include_router(branding.router)
    app.include_router(clients_router.router)
    app.include_router(config_router.router)
    app.include_router(admin_router.router)
    register_error_handlers(app)
    app.dependency_overrides[reasons.get_reasons_store] = get_reasons_store
    app.dependency_overrides[events.get_influx_gateway] = get_influx_gateway
    app.dependency_overrides[branding.get_logo_store] = get_logo_store
    app.dependency_overrides[health.get_influx_gateway] = get_influx_gateway
    app.dependency_overrides[clients_router.get_client_store] = get_client_store
    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: settings
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
    return app


app = create_app()

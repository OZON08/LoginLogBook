"""FastAPI application factory and wiring."""
from fastapi import FastAPI

from app.config import Settings, get_settings
from app.influx import InfluxGateway
from app.logo_store import LogoStore
from app.reasons_store import ReasonsStore
from app.routers import branding, events, health, reasons


def get_reasons_store() -> ReasonsStore:
    return ReasonsStore(get_settings().reasons_file)


def get_influx_gateway() -> InfluxGateway:
    return InfluxGateway(get_settings())


def get_logo_store() -> LogoStore:
    settings = get_settings()
    return LogoStore(settings.logo_dir, settings.logo_max_bytes)


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="LoginLogBook API", version="0.1.0")
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

"""FastAPI application factory and wiring."""
from fastapi import FastAPI

from app.client_store import ClientStore
from app.config import Settings, get_settings
from app.influx import InfluxGateway
from app.logo_store import LogoStore
from app.reasons_store import ReasonsStore
from app.routers import branding, events, health, reasons
from app.routers import admin as admin_router
from app.routers import clients as clients_router


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
    app = FastAPI(title="LoginLogBook API", version="0.1.0")
    app.include_router(health.router)
    app.include_router(reasons.router)
    app.include_router(events.router)
    app.include_router(branding.router)
    app.include_router(clients_router.router)
    app.include_router(admin_router.router)
    app.dependency_overrides[reasons.get_reasons_store] = get_reasons_store
    app.dependency_overrides[events.get_influx_gateway] = get_influx_gateway
    app.dependency_overrides[branding.get_logo_store] = get_logo_store
    app.dependency_overrides[health.get_influx_gateway] = get_influx_gateway
    app.dependency_overrides[clients_router.get_client_store] = get_client_store
    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: settings
    return app


app = create_app()

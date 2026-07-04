"""FastAPI application factory and wiring."""
from fastapi import FastAPI

from app.config import get_settings
from app.influx import InfluxGateway
from app.reasons_store import ReasonsStore
from app.routers import events, health, reasons


def get_reasons_store() -> ReasonsStore:
    """Provide a reasons store backed by the configured file path."""
    return ReasonsStore(get_settings().reasons_file)


def get_influx_gateway() -> InfluxGateway:
    """Provide an InfluxDB gateway backed by current settings."""
    return InfluxGateway(get_settings())


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(title="LoginLogBook API", version="0.1.0")
    app.include_router(health.router)
    app.include_router(reasons.router)
    app.include_router(events.router)
    app.dependency_overrides[reasons.get_reasons_store] = get_reasons_store
    app.dependency_overrides[events.get_influx_gateway] = get_influx_gateway
    return app


app = create_app()

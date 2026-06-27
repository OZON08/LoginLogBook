"""FastAPI application factory and wiring."""
from app.config import get_settings
from fastapi import FastAPI

from app.reasons_store import ReasonsStore
from app.routers import health, reasons


def get_reasons_store() -> ReasonsStore:
    """Provide a reasons store backed by the configured file path."""
    return ReasonsStore(get_settings().reasons_file)


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(title="LoginLogBook API", version="0.1.0")
    app.include_router(health.router)
    app.include_router(reasons.router)
    app.dependency_overrides[reasons.get_reasons_store] = get_reasons_store
    return app


app = create_app()

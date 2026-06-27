"""FastAPI application factory and wiring."""
from fastapi import FastAPI

from app.routers import health


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(title="LoginLogBook API", version="0.1.0")
    app.include_router(health.router)
    return app


app = create_app()

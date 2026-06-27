"""Shared test fixtures."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app
from app.reasons_store import ReasonsStore
from app.routers import reasons as reasons_router


@pytest.fixture
def client() -> TestClient:
    """A TestClient bound to a fresh app instance."""
    return TestClient(create_app())


@pytest.fixture
def configured_client(tmp_path: Path) -> TestClient:
    """A TestClient with temp-file stores and known tokens."""
    app = create_app()
    settings = Settings(
        admin_token="admin-secret",
        client_token="client-secret",
        reasons_file=tmp_path / "reasons.json",
        logo_dir=tmp_path / "logo",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[reasons_router.get_reasons_store] = (
        lambda: ReasonsStore(settings.reasons_file)
    )
    return TestClient(app)

"""Shared test fixtures."""
import pytest

from app.config import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(
        api_url="http://testserver",
        client_token="test-token",
        cache_dir=tmp_path / "cache",
        queue_file=tmp_path / "queue.json",
    )

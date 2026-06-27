"""Application settings loaded from environment variables."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_url: str = "http://localhost:8000"
    client_token: str = ""
    api_ca_bundle: Path | None = None
    cache_dir: Path = Path("~/.loginlogbook/cache").expanduser()
    queue_file: Path = Path("~/.loginlogbook/queue.json").expanduser()


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""Application settings loaded from environment variables."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Values come from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    influx_url: str = "http://influxdb:8086"
    influx_token: str = ""
    influx_org: str = "loginlogbook"
    influx_bucket: str = "logins"

    admin_token: str = ""
    client_token: str = ""

    reasons_file: Path = Path("/data/reasons.json")
    logo_dir: Path = Path("/data/logo")
    logo_max_bytes: int = 2_097_152


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()

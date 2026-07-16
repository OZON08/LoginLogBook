"""Application settings loaded from environment variables."""
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
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
    client_tokens: list[str] = []

    reasons_file: Path = Path("/data/reasons.json")
    logo_dir: Path = Path("/data/logo")
    logo_max_bytes: int = 2_097_152
    clients_file: Path = Path("/data/clients.json")
    branding_file: Path = Path("/data/branding.json")
    settings_file: Path = Path("/data/settings.json")

    @field_validator("client_tokens", mode="before")
    @classmethod
    def _parse_tokens(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v

    def effective_client_tokens(self) -> list[str]:
        """Return client_tokens if set, else [client_token] for backward compat."""
        return self.client_tokens if self.client_tokens else [self.client_token]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()

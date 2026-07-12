"""HTTP client for all loginlogbook-api endpoints."""
import httpx

from app.config import Settings
from app.models import AppConfig, BrandingConfig, EventIn, EventOut, Reason

_TIMEOUT = 5.0


class ApiClient:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base = settings.api_url.rstrip("/")
        self._headers = {"X-Client-Token": settings.client_token}
        self._transport = transport
        self._verify: str | bool = str(settings.api_ca_bundle) if settings.api_ca_bundle else True

    def _get(self, path: str, **params) -> httpx.Response:
        with httpx.Client(transport=self._transport, verify=self._verify) as c:
            r = c.get(
                f"{self._base}{path}",
                headers=self._headers,
                params=params or None,
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            return r

    def get_reasons(self) -> list[Reason]:
        return [Reason(**r) for r in self._get("/reasons").json()]

    def get_logo(self) -> tuple[bytes, str]:
        r = self._get("/branding/logo")
        return r.content, r.headers.get("content-type", "image/png")

    def get_config(self) -> AppConfig:
        return AppConfig(**self._get("/config").json())

    def get_branding_config(self) -> BrandingConfig:
        return BrandingConfig(**self._get("/branding/config").json())

    def get_recent_events(self, host: str, days: int) -> list[EventOut]:
        r = self._get("/events/recent", host=host, days=days, limit=100)
        return [EventOut(**e) for e in r.json()]

    def post_event(self, event: EventIn) -> None:
        with httpx.Client(transport=self._transport, verify=self._verify) as c:
            r = c.post(
                f"{self._base}/events",
                headers=self._headers,
                json=event.model_dump(mode="json"),
                timeout=_TIMEOUT,
            )
            r.raise_for_status()

"""Health endpoint with InfluxDB readiness."""
from importlib.metadata import version as _pkg_version
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.influx import InfluxGateway

_VERSION = _pkg_version("loginlogbook-api")

router = APIRouter()


def get_influx_gateway() -> InfluxGateway:
    """Overridden in app.main with a settings-backed provider."""
    raise NotImplementedError


@router.get("/version", include_in_schema=False)
def get_version() -> dict[str, str]:
    return {"version": _VERSION}


@router.get("/health")
def health(
    response: Response,
    gateway: Annotated[InfluxGateway, Depends(get_influx_gateway)],
) -> dict[str, str]:
    """Readiness probe: ok only when InfluxDB is reachable."""
    if gateway.ping():
        return {"status": "ok", "influxdb": "up"}
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "degraded", "influxdb": "down"}

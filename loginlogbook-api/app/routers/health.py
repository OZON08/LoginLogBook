"""Health endpoint."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. InfluxDB readiness is added in a later task."""
    return {"status": "ok"}

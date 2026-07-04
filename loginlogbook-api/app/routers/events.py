"""Event ingestion and recent-event query endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import require_client
from app.influx import InfluxGateway
from app.models import EventIn, EventOut

router = APIRouter(tags=["events"])


def get_influx_gateway() -> InfluxGateway:
    """Overridden in app.main with a settings-backed provider."""
    raise NotImplementedError


@router.post(
    "/events",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_client)],
)
def record_event(
    event: EventIn,
    gateway: Annotated[InfluxGateway, Depends(get_influx_gateway)],
) -> dict[str, str]:
    try:
        gateway.write_event(event)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Event store unavailable",
        ) from exc
    return {"status": "recorded"}


@router.get(
    "/events/recent",
    dependencies=[Depends(require_client)],
)
def recent_events(
    gateway: Annotated[InfluxGateway, Depends(get_influx_gateway)],
    host: str,
    limit: Annotated[int, Query(ge=1, le=100)] = 5,
    event_type: str | None = None,
) -> list[EventOut]:
    try:
        return gateway.recent_events(host=host, limit=limit, event_type=event_type)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Event store unavailable",
        ) from exc

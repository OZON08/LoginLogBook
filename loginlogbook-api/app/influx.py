"""InfluxDB access layer. The only module that talks to InfluxDB."""
from collections.abc import Callable

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from app.config import Settings
from app.models import EventIn, EventOut

MEASUREMENT = "login_events"


def default_client_factory(settings: Settings) -> InfluxDBClient:
    """Create a real InfluxDB client from settings."""
    return InfluxDBClient(
        url=settings.influx_url, token=settings.influx_token, org=settings.influx_org
    )


class InfluxGateway:
    """Reads and writes login_events points."""

    def __init__(
        self,
        settings: Settings,
        client_factory: Callable[[Settings], InfluxDBClient] = default_client_factory,
    ) -> None:
        self._settings = settings
        self._client_factory = client_factory

    def write_event(self, event: EventIn) -> None:
        """Write a single login/logout event to InfluxDB."""
        point = (
            Point(MEASUREMENT)
            .tag("event_type", event.event_type)
            .tag("host", event.host)
            .tag("os_user", event.os_user)
            .field("count", 1)
            .time(event.timestamp, WritePrecision.NS)
        )
        if event.reason is not None:
            point = point.tag("reason", event.reason)

        client = self._client_factory(self._settings)
        try:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            write_api.write(
                bucket=self._settings.influx_bucket,
                org=self._settings.influx_org,
                record=point,
            )
        finally:
            client.close()

    def recent_events(
        self, host: str, limit: int, event_type: str | None = None
    ) -> list[EventOut]:
        """Return the most recent events for a host, newest first."""
        type_filter = (
            f' and r.event_type == "{event_type}"' if event_type else ""
        )
        flux = (
            f'from(bucket: "{self._settings.influx_bucket}")'
            f" |> range(start: -30d)"
            f' |> filter(fn: (r) => r._measurement == "{MEASUREMENT}"'
            f' and r.host == "{host}"{type_filter})'
            f' |> sort(columns: ["_time"], desc: true)'
            f" |> limit(n: {int(limit)})"
        )
        client = self._client_factory(self._settings)
        try:
            tables = client.query_api().query(flux, org=self._settings.influx_org)
        finally:
            client.close()

        events: list[EventOut] = []
        for table in tables:
            for record in table.records:
                events.append(
                    EventOut(
                        event_type=record.values.get("event_type"),
                        host=record.values.get("host"),
                        os_user=record.values.get("os_user"),
                        reason=record.values.get("reason"),
                        timestamp=record.get_time(),
                    )
                )
        return events

    def ping(self) -> bool:
        """Return True if InfluxDB responds to a ping."""
        client = self._client_factory(self._settings)
        try:
            return bool(client.ping())
        except Exception:
            return False
        finally:
            client.close()

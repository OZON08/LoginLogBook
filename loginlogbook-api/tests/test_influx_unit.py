"""Unit tests for the InfluxDB gateway using a fake client."""
from datetime import datetime, timezone

from app.config import Settings
from app.influx import InfluxGateway
from app.models import EventIn


class FakeWriteApi:
    def __init__(self):
        self.written = []

    def write(self, bucket, org, record):
        self.written.append((bucket, org, record))


class FakeQueryApi:
    def __init__(self, tables=None):
        self._tables = tables or []
        self.last_flux: str = ""

    def query(self, flux, org):
        self.last_flux = flux
        return self._tables


class FakeClient:
    def __init__(self, tables=None):
        self._write_api = FakeWriteApi()
        self._query_api = FakeQueryApi(tables)

    def write_api(self, **kwargs):
        return self._write_api

    def query_api(self):
        return self._query_api

    def ping(self):
        return True

    def close(self):
        pass


class FakePingFailClient(FakeClient):
    def ping(self):
        raise ConnectionError("unreachable")


def _settings() -> Settings:
    return Settings(
        influx_bucket="logins", influx_org="loginlogbook", influx_token="t"
    )


def test_write_event_builds_point_with_tags():
    fake = FakeClient()
    gateway = InfluxGateway(_settings(), client_factory=lambda s: fake)
    event = EventIn(
        event_type="login",
        host="srv01",
        os_user="alice",
        reason="Maintenance",
        timestamp=datetime(2026, 6, 26, 8, 0, tzinfo=timezone.utc),
    )
    gateway.write_event(event)
    assert len(fake._write_api.written) == 1
    bucket, org, point = fake._write_api.written[0]
    assert bucket == "logins"
    assert org == "loginlogbook"
    line = point.to_line_protocol()
    assert line.startswith("login_events,")
    assert "event_type=login" in line
    assert "host=srv01" in line
    assert "os_user=alice" in line
    assert "reason=Maintenance" in line


def test_write_event_omits_reason_tag_for_logout():
    fake = FakeClient()
    gateway = InfluxGateway(_settings(), client_factory=lambda s: fake)
    event = EventIn(
        event_type="logout",
        host="srv01",
        os_user="alice",
        reason=None,
        timestamp=datetime(2026, 6, 26, 9, 0, tzinfo=timezone.utc),
    )
    gateway.write_event(event)
    _, _, point = fake._write_api.written[0]
    line = point.to_line_protocol()
    assert "reason" not in line
    assert "event_type=logout" in line


def test_write_event_field_count_is_one():
    fake = FakeClient()
    gateway = InfluxGateway(_settings(), client_factory=lambda s: fake)
    event = EventIn(
        event_type="login",
        host="srv02",
        os_user="bob",
        timestamp=datetime(2026, 6, 26, 10, 0, tzinfo=timezone.utc),
    )
    gateway.write_event(event)
    _, _, point = fake._write_api.written[0]
    line = point.to_line_protocol()
    assert "count=1i" in line


def test_ping_delegates_to_client():
    fake = FakeClient()
    gateway = InfluxGateway(_settings(), client_factory=lambda s: fake)
    assert gateway.ping() is True


def test_ping_returns_false_on_exception():
    fail_client = FakePingFailClient()
    gateway = InfluxGateway(_settings(), client_factory=lambda s: fail_client)
    assert gateway.ping() is False


def test_recent_events_returns_empty_list_when_no_data():
    fake = FakeClient(tables=[])
    gateway = InfluxGateway(_settings(), client_factory=lambda s: fake)
    result = gateway.recent_events(host="srv01", limit=10)
    assert result == []


def test_write_logout_with_reason_omits_reason_tag():
    """Logout events must never carry a reason tag even when reason is set."""
    fake = FakeClient()
    gateway = InfluxGateway(_settings(), client_factory=lambda s: fake)
    event = EventIn(
        event_type="logout",
        host="srv01",
        os_user="alice",
        reason="Session expired",
        timestamp=datetime(2026, 6, 26, 9, 0, tzinfo=timezone.utc),
    )
    gateway.write_event(event)
    _, _, point = fake._write_api.written[0]
    line = point.to_line_protocol()
    assert "reason" not in line
    assert "event_type=logout" in line


def test_recent_events_uses_days_parameter():
    """recent_events(days=7) must pass -7d into the Flux range filter."""
    fake = FakeClient(tables=[])
    gateway = InfluxGateway(_settings(), client_factory=lambda s: fake)
    gateway.recent_events(host="srv1", limit=10, days=7)
    assert "-7d" in fake._query_api.last_flux
    assert "-30d" not in fake._query_api.last_flux

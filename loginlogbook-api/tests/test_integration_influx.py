"""Integration test against a real InfluxDB. Skipped unless explicitly enabled.

Enable with:
    LLB_INTEGRATION=1 INFLUX_URL=... INFLUX_TOKEN=... INFLUX_ORG=... \
    INFLUX_BUCKET=... pytest tests/test_integration_influx.py
"""
import os
import uuid
from datetime import datetime, timezone

import pytest

from app.config import Settings
from app.influx import InfluxGateway
from app.models import EventIn

pytestmark = pytest.mark.skipif(
    os.getenv("LLB_INTEGRATION") != "1",
    reason="integration test disabled (set LLB_INTEGRATION=1)",
)


def test_write_then_read_event():
    settings = Settings()
    gateway = InfluxGateway(settings)
    host = f"itest-{uuid.uuid4().hex[:8]}"
    event = EventIn(
        event_type="login",
        host=host,
        os_user="tester",
        reason="Integration",
        timestamp=datetime.now(timezone.utc),
    )
    gateway.write_event(event)

    recent = gateway.recent_events(host=host, limit=5)
    assert any(e.os_user == "tester" and e.reason == "Integration" for e in recent)

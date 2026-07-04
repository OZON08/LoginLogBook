"""Tests for the events endpoints."""

CLIENT = {"X-Client-Token": "client-secret"}


def _login_payload(host="srv01", user="alice", reason="Maintenance"):
    return {
        "event_type": "login",
        "host": host,
        "os_user": user,
        "reason": reason,
        "timestamp": "2026-06-26T08:00:00+00:00",
    }


def test_record_event_requires_client_token(events_client):
    assert events_client.post("/events", json=_login_payload()).status_code == 403


def test_record_event_succeeds(events_client):
    resp = events_client.post("/events", json=_login_payload(), headers=CLIENT)
    assert resp.status_code == 201


def test_record_event_returns_503_when_store_down(events_client, fake_gateway):
    fake_gateway.fail = True
    resp = events_client.post("/events", json=_login_payload(), headers=CLIENT)
    assert resp.status_code == 503


def test_recent_events_filters_by_host(events_client):
    events_client.post("/events", json=_login_payload(host="srv01"), headers=CLIENT)
    events_client.post("/events", json=_login_payload(host="srv02"), headers=CLIENT)
    resp = events_client.get("/events/recent", params={"host": "srv01"}, headers=CLIENT)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["host"] == "srv01"


def test_recent_events_respects_limit(events_client):
    for i in range(7):
        events_client.post(
            "/events", json=_login_payload(user=f"u{i}"), headers=CLIENT
        )
    resp = events_client.get(
        "/events/recent", params={"host": "srv01", "limit": 3}, headers=CLIENT
    )
    assert len(resp.json()) == 3


def test_recent_events_requires_client_token(events_client):
    resp = events_client.get("/events/recent", params={"host": "srv01"})
    assert resp.status_code == 403


def test_recent_events_returns_503_when_store_down(events_client, fake_gateway):
    fake_gateway.fail = True
    resp = events_client.get(
        "/events/recent", params={"host": "srv01"}, headers=CLIENT
    )
    assert resp.status_code == 503

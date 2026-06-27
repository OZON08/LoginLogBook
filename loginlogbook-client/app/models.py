"""Data models matching the loginlogbook-api HTTP contract."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

EventType = Literal["login", "logout"]


class Reason(BaseModel):
    id: str
    label: str
    active: bool = True


class EventIn(BaseModel):
    event_type: EventType
    host: str
    os_user: str
    reason: str | None = None
    timestamp: datetime


class EventOut(BaseModel):
    event_type: EventType
    host: str
    os_user: str
    reason: str | None = None
    timestamp: datetime


class AppConfig(BaseModel):
    recent_days: int = 7

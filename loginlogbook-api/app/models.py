"""Pydantic request and response models."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EventType = Literal["login", "logout"]


class ReasonIn(BaseModel):
    """Payload for creating a reason."""

    label: str


class Reason(BaseModel):
    """A selectable login reason."""

    id: str
    label: str
    active: bool = True


class EventIn(BaseModel):
    """Payload for recording a login/logout event."""

    event_type: EventType
    host: str
    os_user: str
    reason: str | None = None
    timestamp: datetime


class EventOut(BaseModel):
    """A recorded event returned by recent-event queries."""

    event_type: EventType
    host: str
    os_user: str
    reason: str | None = None
    timestamp: datetime


class ClientIn(BaseModel):
    """Payload for registering a new client."""

    name: str
    token: str = Field(min_length=1)


class ClientOut(BaseModel):
    """A registered client (token intentionally omitted)."""

    name: str

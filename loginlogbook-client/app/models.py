"""Data models matching the loginlogbook-api HTTP contract."""
from datetime import datetime
from typing import Literal

import re

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
    allow_free_text: bool = True


_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


class BrandingConfig(BaseModel):
    logo_height: int = 120
    logo_bg: str = "#1E293B"

    @property
    def safe_logo_bg(self) -> str:
        return self.logo_bg if _HEX_COLOR.match(self.logo_bg) else "#1E293B"

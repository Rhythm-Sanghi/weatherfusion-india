from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.domain.events import EventCategory


@dataclass(frozen=True, slots=True)
class NormalizedEventInput:
    source_name: str
    source_type: str
    external_id: str | None
    event_type: EventCategory
    severity: str
    title: str
    description: str | None
    raw_text: str
    latitude: float | None
    longitude: float | None
    state: str | None
    district: str | None
    city: str | None
    observed_at: datetime
    metadata: dict[str, Any]

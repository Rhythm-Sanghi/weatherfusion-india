from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class NearbyEventResponse(BaseModel):
    id: UUID
    relationship: str
    distance_meters: float
    observed_at: datetime | None
    title: str | None
    event_type: str | None
    source_name: str | None


class NearbyEventsResponse(BaseModel):
    source_event_id: UUID
    radius_meters: float
    filters: dict[str, Any]
    provider: dict[str, str]
    items: list[NearbyEventResponse]


class GeoJsonFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[dict[str, Any]]

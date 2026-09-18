from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.events import EventCategory, ProcessingStatus, SystemAssessment
from app.domain.reviews import AdminStatus


class EventCreate(BaseModel):
    source: str = Field(min_length=1, max_length=160)
    source_type: str = Field(default="CITIZEN", min_length=1, max_length=64)
    external_id: str | None = Field(default=None, max_length=160)
    event_type: EventCategory
    severity: str = Field(min_length=1, max_length=32)
    title: str | None = Field(default=None, max_length=240)
    description: str | None = None
    raw_text: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    state: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    observed_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "source",
        "source_type",
        "external_id",
        "title",
        "description",
        "raw_text",
        "state",
        "district",
        "city",
        mode="before",
    )
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @field_validator("observed_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_event_text(self) -> "EventCreate":
        if not self.raw_text and not self.description:
            raise ValueError("description or raw_text is required")
        return self


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    source_type: str
    reliability: float | None
    enabled: bool


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
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
    received_at: datetime
    created_at: datetime
    updated_at: datetime
    processing_status: ProcessingStatus
    system_assessment: SystemAssessment
    admin_status: AdminStatus
    version: int
    metadata: dict[str, Any]
    source: SourceResponse

    @classmethod
    def from_event(cls, event: Any) -> "EventResponse":
        return cls.model_validate(
            {
                "id": event.id,
                "external_id": event.external_id,
                "event_type": event.event_type,
                "severity": event.severity,
                "title": event.title,
                "description": event.description,
                "raw_text": event.raw_text,
                "latitude": event.latitude,
                "longitude": event.longitude,
                "state": event.state,
                "district": event.district,
                "city": event.city,
                "observed_at": event.observed_at,
                "received_at": event.received_at,
                "created_at": event.created_at,
                "updated_at": event.updated_at,
                "processing_status": event.processing_status,
                "system_assessment": event.system_assessment,
                "admin_status": event.admin_status,
                "version": event.version,
                "metadata": event.metadata_,
                "source": event.source,
            }
        )


class EventListResponse(BaseModel):
    items: list[EventResponse]
    page: int
    page_size: int
    total: int


class EventSummaryResponse(BaseModel):
    total_events: int
    by_processing_status: dict[str, int]
    by_system_assessment: dict[str, int]
    by_admin_status: dict[str, int]

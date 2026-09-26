from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.domain.events import EventCategory


class MediaEvidenceCreate(BaseModel):
    media_type: Literal["IMAGE", "VIDEO"]
    reference: str = Field(min_length=1, max_length=500)
    mime_type: str | None = Field(default=None, max_length=100)
    caption: str | None = Field(default=None, max_length=500)

    @field_validator("reference", "mime_type", "caption", mode="before")
    @classmethod
    def trim_media_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @field_validator("reference")
    @classmethod
    def allow_safe_reference(cls, value: str) -> str:
        if not (value.startswith("https://") or value.startswith("demo://")):
            raise ValueError("media reference must use https:// or demo://")
        return value


class CitizenReportCreate(BaseModel):
    """Small, privacy-preserving input contract for controlled citizen reports."""

    description: str = Field(min_length=1, max_length=4000)
    event_type: EventCategory | None = None
    severity: str | None = Field(default=None, max_length=32)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    observed_at: datetime
    state: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    reporter_alias: str | None = Field(default=None, max_length=100)
    media: list[MediaEvidenceCreate] = Field(default_factory=list, max_length=3)

    @field_validator("description", "severity", "state", "district", "city", "reporter_alias", mode="before")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @field_validator("description")
    @classmethod
    def require_description(cls, value: str) -> str:
        if not value:
            raise ValueError("description is required")
        return value

    @field_validator("observed_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

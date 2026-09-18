from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.reviews import AdminStatus, ReviewAction
from app.schemas.events import EventResponse


class ReviewRequest(BaseModel):
    action: ReviewAction
    reviewer_id: str = Field(min_length=1, max_length=100)
    reviewer_name: str = Field(min_length=1, max_length=160)
    reason: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=2000)
    expected_version: int = Field(ge=1)

    @field_validator("reviewer_id", "reviewer_name", "reason", "notes", mode="before")
    @classmethod
    def trim(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class ReviewDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_id: UUID
    action: ReviewAction
    previous_admin_status: AdminStatus
    new_admin_status: AdminStatus
    reviewer_id: str
    reviewer_name: str
    reason: str
    notes: str | None
    event_version: int
    created_at: datetime


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_id: UUID
    event_type: str
    action: str
    actor_type: str
    actor_id: str
    actor_name: str
    previous_value: str | None
    new_value: str | None
    reason: str | None
    created_at: datetime


class ReviewQueueItem(EventResponse):
    attention_reason: str


class ReviewEventDetail(BaseModel):
    event: EventResponse
    attention_reason: str
    audit: list[AuditEventResponse]

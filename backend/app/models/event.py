from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import Uuid

from app.db import Base
from app.domain.events import EventCategory, ProcessingStatus, SystemAssessment
from app.domain.reviews import AdminStatus, ReviewAction


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(64), index=True)
    reliability: Mapped[float | None] = mapped_column(nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list["WeatherEvent"]] = relationship(back_populates="source")


class RawIngestRecord(Base):
    __tablename__ = "raw_ingest_records"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    validation_status: Mapped[str] = mapped_column(String(32), default="ACCEPTED")
    validation_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class WeatherEvent(Base):
    __tablename__ = "weather_events"
    __table_args__ = (
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)", name="ck_events_latitude"
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="ck_events_longitude",
        ),
        Index(
            "uq_weather_events_source_external_id",
            "source_id",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
            sqlite_where=text("external_id IS NOT NULL"),
        ),
        Index("ix_weather_events_filters", "event_type", "state", "severity"),
        Index(
            "ix_weather_events_statuses", "processing_status", "system_assessment", "admin_status"
        ),
        Index("ix_weather_events_observed_at", "observed_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    event_type: Mapped[EventCategory] = mapped_column(
        Enum(EventCategory, native_enum=False), index=True
    )
    severity: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, native_enum=False), default=ProcessingStatus.RECEIVED, index=True
    )
    system_assessment: Mapped[SystemAssessment] = mapped_column(
        Enum(SystemAssessment, native_enum=False), default=SystemAssessment.PENDING, index=True
    )
    admin_status: Mapped[AdminStatus] = mapped_column(
        Enum(AdminStatus, native_enum=False), default=AdminStatus.UNREVIEWED, index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    source: Mapped[Source] = relationship(back_populates="events")


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("weather_events.id"), index=True)
    action: Mapped[ReviewAction] = mapped_column(Enum(ReviewAction, native_enum=False))
    previous_admin_status: Mapped[AdminStatus] = mapped_column(Enum(AdminStatus, native_enum=False))
    new_admin_status: Mapped[AdminStatus] = mapped_column(Enum(AdminStatus, native_enum=False))
    reviewer_id: Mapped[str] = mapped_column(String(100))
    reviewer_name: Mapped[str] = mapped_column(String(160))
    reason: Mapped[str] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("weather_events.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    actor_type: Mapped[str] = mapped_column(String(32))
    actor_id: Mapped[str] = mapped_column(String(100))
    actor_name: Mapped[str] = mapped_column(String(160))
    previous_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

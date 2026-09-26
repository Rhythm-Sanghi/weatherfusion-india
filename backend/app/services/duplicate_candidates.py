"""Bounded PostGIS candidate retrieval for deterministic duplicate ranking."""
from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from app.domain.events import EventCategory
from app.domain.providers import CandidateEvent
from app.models.event import WeatherEvent
from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session


def retrieve_duplicate_candidates(
    session: Session, *, event_id: UUID, latitude: float | None, longitude: float | None,
    observed_at: datetime | None,
    event_type: EventCategory,
    radius_meters: float = 20_000,
    time_window_hours: int = 24, limit: int = 25,
) -> list[CandidateEvent]:
    """Return bounded nearby historical candidates; missing spatial/time inputs return none."""
    if latitude is None or longitude is None or observed_at is None:
        return []
    # Reuse the event's generated geography point so ST_DWithin stays in metre
    # semantics without relying on an untyped SQLAlchemy cast literal.
    point = select(WeatherEvent.location).where(WeatherEvent.id == event_id).scalar_subquery()
    statement = (
        select(
            WeatherEvent.id,
            WeatherEvent.raw_text,
            WeatherEvent.observed_at,
            WeatherEvent.latitude,
            WeatherEvent.longitude,
        )
        .where(
            WeatherEvent.id != event_id,
            WeatherEvent.location.is_not(None),
            WeatherEvent.observed_at.between(
                observed_at - timedelta(hours=time_window_hours), observed_at + timedelta(hours=time_window_hours)
            ),
            func.ST_DWithin(WeatherEvent.location, point, radius_meters),
        )
        .order_by(WeatherEvent.observed_at.desc(), cast(WeatherEvent.id, String))
        .limit(limit)
    )
    if event_type is not EventCategory.UNKNOWN:
        statement = statement.where(WeatherEvent.event_type == event_type)
    return [
        CandidateEvent(
            row.id,
            row.raw_text,
            row.observed_at,
            row.latitude,
            row.longitude,
        )
        for row in session.execute(statement)
    ]

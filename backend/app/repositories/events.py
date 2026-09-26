from datetime import datetime
from uuid import UUID

from app.domain.events import EventCategory, ProcessingStatus, SystemAssessment
from app.domain.reviews import AdminStatus
from app.models.event import Source, WeatherEvent
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, joinedload, selectinload


class EventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_or_create_source(self, name: str, source_type: str) -> Source:
        source = self.session.scalar(select(Source).where(Source.name == name))
        if source is None:
            source = Source(name=name, source_type=source_type)
            self.session.add(source)
            self.session.flush()
        return source

    def find_by_external_id(self, source_id: UUID, external_id: str | None) -> WeatherEvent | None:
        if external_id is None:
            return None
        return self.session.scalar(
            select(WeatherEvent).where(
                WeatherEvent.source_id == source_id, WeatherEvent.external_id == external_id
            )
        )

    def get(self, event_id: UUID) -> WeatherEvent | None:
        return self.session.scalar(
            select(WeatherEvent)
            .options(joinedload(WeatherEvent.source), selectinload(WeatherEvent.media_evidence))
            .where(WeatherEvent.id == event_id)
        )

    def list(
        self,
        *,
        page: int,
        page_size: int,
        event_type: EventCategory | None = None,
        state: str | None = None,
        severity: str | None = None,
        processing_status: ProcessingStatus | None = None,
        system_assessment: SystemAssessment | None = None,
        admin_status: AdminStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        boundary_id: UUID | None = None,
    ) -> tuple[list[WeatherEvent], int]:
        statement = select(WeatherEvent).options(
            joinedload(WeatherEvent.source), selectinload(WeatherEvent.media_evidence)
        )
        count_statement = select(func.count()).select_from(WeatherEvent)
        filters = []
        if event_type is not None:
            filters.append(WeatherEvent.event_type == event_type)
        if state is not None:
            filters.append(WeatherEvent.state == state)
        if severity is not None:
            filters.append(WeatherEvent.severity == severity)
        if processing_status is not None:
            filters.append(WeatherEvent.processing_status == processing_status)
        if system_assessment is not None:
            filters.append(WeatherEvent.system_assessment == system_assessment)
        if admin_status is not None:
            filters.append(WeatherEvent.admin_status == admin_status)
        if date_from is not None:
            filters.append(WeatherEvent.observed_at >= date_from)
        if date_to is not None:
            filters.append(WeatherEvent.observed_at <= date_to)
        if boundary_id is not None:
            filters.append(
                text(
                    """EXISTS (SELECT 1 FROM administrative_boundaries ab
                    WHERE ab.id = CAST(:boundary_id AS uuid)
                    AND weather_events.location IS NOT NULL
                    AND ST_Covers(ab.geometry, weather_events.location::geometry))"""
                ).bindparams(boundary_id=str(boundary_id))
            )
        if filters:
            statement = statement.where(*filters)
            count_statement = count_statement.where(*filters)
        events = (
            self.session.scalars(
                statement.order_by(WeatherEvent.observed_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .unique()
            .all()
        )
        return events, self.session.scalar(count_statement) or 0

    def summary(self) -> tuple[int, dict[str, int], dict[str, int], dict[str, int]]:
        total = self.session.scalar(select(func.count()).select_from(WeatherEvent)) or 0
        return (
            total,
            self._count_by(WeatherEvent.processing_status),
            self._count_by(WeatherEvent.system_assessment),
            self._count_by(WeatherEvent.admin_status),
        )

    def _count_by(self, column: object) -> dict[str, int]:
        rows = self.session.execute(select(column, func.count()).group_by(column)).all()
        return {str(value): count for value, count in rows}

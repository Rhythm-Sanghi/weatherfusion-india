from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import get_db_session
from app.domain.events import ProcessingStatus, SystemAssessment
from app.domain.reviews import AdminStatus
from app.models.event import Source, WeatherEvent

router = APIRouter(tags=["operations"])
SessionDep = Annotated[Session, Depends(get_db_session)]


def counts(session: Session, column: object) -> dict[str, int]:
    return {str(key): value for key, value in session.execute(select(column, func.count()).group_by(column)).all()}


@router.get("/analytics/overview")
def analytics_overview(session: SessionDep) -> dict[str, int]:
    total = session.scalar(select(func.count()).select_from(WeatherEvent)) or 0
    admin, assessment, processing = counts(session, WeatherEvent.admin_status), counts(session, WeatherEvent.system_assessment), counts(session, WeatherEvent.processing_status)
    return {"total_events": total, "unreviewed_events": admin.get(str(AdminStatus.UNREVIEWED), 0), "verified_events": admin.get(str(AdminStatus.VERIFIED), 0), "rejected_events": admin.get(str(AdminStatus.REJECTED), 0), "escalated_events": admin.get(str(AdminStatus.ESCALATED), 0), "needs_review": assessment.get(str(SystemAssessment.NEEDS_REVIEW), 0), "disputed": assessment.get(str(SystemAssessment.DISPUTED), 0), "partial_processing": processing.get(str(ProcessingStatus.PARTIAL), 0)}


@router.get("/analytics/distribution")
def analytics_distribution(session: SessionDep) -> dict[str, dict[str, int]]:
    return {"event_type": counts(session, WeatherEvent.event_type), "severity": counts(session, WeatherEvent.severity), "state": counts(session, WeatherEvent.state), "system_assessment": counts(session, WeatherEvent.system_assessment), "admin_status": counts(session, WeatherEvent.admin_status)}


@router.get("/analytics/trends")
def analytics_trends(session: SessionDep) -> dict[str, list[dict[str, object]]]:
    rows = session.execute(select(func.date(WeatherEvent.observed_at), func.count()).group_by(func.date(WeatherEvent.observed_at)).order_by(func.date(WeatherEvent.observed_at))).all()
    return {"bucket": "daily observed_at", "items": [{"date": str(day), "count": count} for day, count in rows]}


@router.get("/sources")
def sources(session: SessionDep) -> list[dict[str, object]]:
    rows = session.execute(select(Source, func.count(WeatherEvent.id), func.max(WeatherEvent.received_at)).outerjoin(WeatherEvent).group_by(Source.id)).all()
    return [{"id": str(source.id), "name": source.name, "source_type": source.source_type, "enabled": source.enabled, "event_count": count, "last_activity": last.isoformat() if last else None, "status": "demo fixture" if source.source_type == "DEMO" else ("configured" if source.enabled else "disabled")} for source, count, last in rows]


@router.get("/system/status")
def system_status(session: SessionDep) -> dict[str, object]:
    try:
        session.execute(text("SELECT 1"))
        database = {"status": "operational"}
    except Exception:
        database = {"status": "unavailable"}
    settings = get_settings()
    return {"api": {"status": "operational"}, "database": database, "verification_provider": {"status": "available", "adapter": "connected", "implementation": settings.verification_provider}, "geospatial_provider": {"status": "available", "adapter": "connected", "implementation": settings.geospatial_provider}}

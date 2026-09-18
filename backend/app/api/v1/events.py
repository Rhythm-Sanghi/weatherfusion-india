from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_geospatial_provider, get_verification_provider
from app.db import get_db_session
from app.domain.events import EventCategory, ProcessingStatus, SystemAssessment
from app.domain.providers import GeospatialProvider, VerificationProvider
from app.domain.reviews import AdminStatus
from app.repositories.events import EventRepository
from app.schemas.events import EventCreate, EventListResponse, EventResponse, EventSummaryResponse
from app.services.ingestion import DuplicateExternalIdError, IngestionService

router = APIRouter(prefix="/events", tags=["events"])
SessionDep = Annotated[Session, Depends(get_db_session)]
VerificationProviderDep = Annotated[VerificationProvider, Depends(get_verification_provider)]
GeospatialProviderDep = Annotated[GeospatialProvider, Depends(get_geospatial_provider)]


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    session: SessionDep,
    verification_provider: VerificationProviderDep,
    geospatial_provider: GeospatialProviderDep,
) -> EventResponse:
    service = IngestionService(session, verification_provider, geospatial_provider)
    try:
        event = await service.ingest(payload, payload.model_dump(mode="json"))
    except DuplicateExternalIdError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An event with this source and external_id already exists.",
        ) from exc
    return EventResponse.from_event(event)


@router.get("", response_model=EventListResponse)
def list_events(
    session: SessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    event_type: EventCategory | None = None,
    state: str | None = None,
    severity: str | None = None,
    processing_status: ProcessingStatus | None = None,
    system_assessment: SystemAssessment | None = None,
    admin_status: AdminStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> EventListResponse:
    events, total = EventRepository(session).list(
        page=page,
        page_size=page_size,
        event_type=event_type,
        state=state,
        severity=severity,
        processing_status=processing_status,
        system_assessment=system_assessment,
        admin_status=admin_status,
        date_from=date_from,
        date_to=date_to,
    )
    return EventListResponse(
        items=[EventResponse.from_event(event) for event in events],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/summary", response_model=EventSummaryResponse)
def event_summary(session: SessionDep) -> EventSummaryResponse:
    total, processing, assessment, admin = EventRepository(session).summary()
    return EventSummaryResponse(
        total_events=total,
        by_processing_status=processing,
        by_system_assessment=assessment,
        by_admin_status=admin,
    )


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: UUID, session: SessionDep) -> EventResponse:
    event = EventRepository(session).get(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    return EventResponse.from_event(event)

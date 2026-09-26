from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_geospatial_provider, get_verification_provider
from app.core.config import get_settings
from app.db import get_db_session
from app.domain.events import EventCategory, ProcessingStatus, SystemAssessment
from app.domain.providers import (
    GeospatialEventInput,
    GeospatialProvider,
    MapEventFilters,
    NearbyQuery,
    VerificationProvider,
)
from app.domain.reviews import AdminStatus
from app.repositories.events import EventRepository
from app.schemas.events import EventCreate, EventListResponse, EventResponse, EventSummaryResponse
from app.schemas.spatial import GeoJsonFeatureCollection, NearbyEventResponse, NearbyEventsResponse
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
    boundary_id: UUID | None = None,
) -> EventListResponse:
    if boundary_id is not None and session.scalar(
        text("SELECT 1 FROM administrative_boundaries WHERE id=CAST(:id AS uuid)"),
        {"id": str(boundary_id)},
    ) is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown boundary_id.")
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
        boundary_id=boundary_id,
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


@router.get("/{event_id}/nearby", response_model=NearbyEventsResponse)
async def nearby_events(
    event_id: UUID,
    session: SessionDep,
    geospatial_provider: GeospatialProviderDep,
    radius_meters: float = Query(default=5_000, gt=0, le=100_000),
    limit: int = Query(default=20, ge=1, le=100),
    event_type: EventCategory | None = None,
    severity: str | None = None,
    processing_status: ProcessingStatus | None = None,
    system_assessment: SystemAssessment | None = None,
    admin_status: AdminStatus | None = None,
    source_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> NearbyEventsResponse:
    event = EventRepository(session).get(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    if event.latitude is None or event.longitude is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Event has no coordinates.")
    query = NearbyQuery(
        radius_meters=radius_meters,
        limit=limit,
        observed_after=date_from,
        observed_before=date_to,
        event_type=event_type,
        severity=severity,
        processing_status=processing_status,
        system_assessment=system_assessment,
        admin_status=admin_status,
        source_type=source_type,
    )
    try:
        items = await geospatial_provider.find_nearby(
            GeospatialEventInput(
                event.id,
                event.latitude,
                event.longitude,
                event.observed_at,
                event.state,
                event.district,
                event.city,
            ),
            query,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Geospatial provider is unavailable.") from exc
    return NearbyEventsResponse(
        source_event_id=event.id,
        radius_meters=radius_meters,
        filters={
            "event_type": event_type,
            "severity": severity,
            "processing_status": processing_status,
            "system_assessment": system_assessment,
            "admin_status": admin_status,
            "source_type": source_type,
            "date_from": date_from,
            "date_to": date_to,
        },
        provider={
            "name": items[0].metadata.provider_name
            if items
            else get_settings().geospatial_provider,
            "version": items[0].metadata.provider_version if items else "unknown",
        },
        items=[
            NearbyEventResponse(
                id=item.event_id,
                relationship=item.relationship,
                distance_meters=item.distance_meters or 0,
                observed_at=item.observed_at,
                title=item.title,
                event_type=item.event_type.value if item.event_type else None,
                source_name=item.source_name,
            )
            for item in items
        ],
    )


@router.get("/map/events", response_model=GeoJsonFeatureCollection)
async def map_events(
    session: SessionDep,
    geospatial_provider: GeospatialProviderDep,
    event_type: EventCategory | None = None,
    severity: str | None = None,
    processing_status: ProcessingStatus | None = None,
    system_assessment: SystemAssessment | None = None,
    admin_status: AdminStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    boundary_id: UUID | None = None,
    limit: int = Query(default=500, ge=1, le=1_000),
) -> GeoJsonFeatureCollection:
    if boundary_id is not None and session.scalar(
        text("SELECT 1 FROM administrative_boundaries WHERE id=CAST(:id AS uuid)"),
        {"id": str(boundary_id)},
    ) is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown boundary_id.")
    try:
        features = await geospatial_provider.geojson_features(
            MapEventFilters(
                event_type=event_type,
                severity=severity,
                processing_status=processing_status,
                system_assessment=system_assessment,
                admin_status=admin_status,
                observed_after=date_from,
                observed_before=date_to,
                boundary_id=boundary_id,
                limit=limit,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Geospatial provider is unavailable.") from exc
    return GeoJsonFeatureCollection(features=features)


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: UUID, session: SessionDep) -> EventResponse:
    event = EventRepository(session).get(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    return EventResponse.from_event(event)

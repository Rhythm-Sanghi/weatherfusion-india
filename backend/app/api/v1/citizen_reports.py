from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_geospatial_provider, get_verification_provider
from app.db import get_db_session
from app.domain.events import EventCategory
from app.domain.providers import GeospatialProvider, VerificationProvider
from app.schemas.citizen_reports import CitizenReportCreate
from app.schemas.events import EventCreate, EventResponse
from app.services.ingestion import IngestionService
from app.services.media import attach_media_evidence

router = APIRouter(prefix="/reports", tags=["citizen reports"])
SessionDep = Annotated[Session, Depends(get_db_session)]
VerificationProviderDep = Annotated[VerificationProvider, Depends(get_verification_provider)]
GeospatialProviderDep = Annotated[GeospatialProvider, Depends(get_geospatial_provider)]


@router.post("/citizen", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def submit_citizen_report(
    payload: CitizenReportCreate,
    session: SessionDep,
    verification_provider: VerificationProviderDep,
    geospatial_provider: GeospatialProviderDep,
) -> EventResponse:
    submission_id = uuid4().hex
    raw_payload: dict[str, Any] = payload.model_dump(mode="json")
    raw_payload["submission_id"] = submission_id
    event_payload = EventCreate(
        source="Citizen weather reports",
        source_type="CITIZEN_REPORT",
        external_id=f"citizen:{submission_id}",
        event_type=payload.event_type or EventCategory.UNKNOWN,
        severity=payload.severity or "UNSPECIFIED",
        description=payload.description,
        raw_text=payload.description,
        latitude=payload.latitude,
        longitude=payload.longitude,
        state=payload.state,
        district=payload.district,
        city=payload.city,
        observed_at=payload.observed_at,
        metadata={
            "origin_mode": "CITIZEN_REPORT",
            "submission_id": submission_id,
            **({"reporter_alias": payload.reporter_alias} if payload.reporter_alias else {}),
            "media_count": len(payload.media),
        },
    )
    event = await IngestionService(session, verification_provider, geospatial_provider).ingest(
        event_payload, raw_payload
    )
    if payload.media:
        attach_media_evidence(session, event, payload.media, source_name="Citizen Report", is_demo=False)
    return EventResponse.from_event(event)

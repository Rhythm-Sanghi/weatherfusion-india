from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.schemas.events import EventResponse
from app.schemas.reviews import (
    AuditEventResponse,
    ReviewDecisionResponse,
    ReviewEventDetail,
    ReviewQueueItem,
    ReviewRequest,
)
from app.services.reviews import ReviewConflictError, ReviewError, ReviewService

router = APIRouter(tags=["reviews"])
SessionDep = Annotated[Session, Depends(get_db_session)]


@router.get("/review-queue", response_model=list[ReviewQueueItem])
def review_queue(session: SessionDep) -> list[ReviewQueueItem]:
    service = ReviewService(session)
    return [ReviewQueueItem(**EventResponse.from_event(event).model_dump(), attention_reason=service.attention_reason(event)) for event in service.queue()]


@router.get("/review-queue/{event_id}", response_model=ReviewEventDetail)
def review_detail(event_id: UUID, session: SessionDep) -> ReviewEventDetail:
    service = ReviewService(session)
    event = service.get(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    return ReviewEventDetail(event=EventResponse.from_event(event), attention_reason=service.attention_reason(event), audit=[AuditEventResponse.model_validate(item) for item in service.audit(event_id)])


@router.post("/events/{event_id}/reviews", response_model=ReviewDecisionResponse)
def submit_review(event_id: UUID, payload: ReviewRequest, session: SessionDep) -> ReviewDecisionResponse:
    try:
        decision, _ = ReviewService(session).decide(event_id, payload)
    except ReviewConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ReviewError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST if str(exc) != "Event not found." else status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ReviewDecisionResponse.model_validate(decision)


@router.get("/events/{event_id}/audit", response_model=list[AuditEventResponse])
def event_audit(event_id: UUID, session: SessionDep) -> list[AuditEventResponse]:
    service = ReviewService(session)
    if service.get(event_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    return [AuditEventResponse.model_validate(item) for item in service.audit(event_id)]

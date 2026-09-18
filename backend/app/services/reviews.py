from uuid import UUID

from app.domain.events import ProcessingStatus, SystemAssessment
from app.domain.reviews import AdminStatus, ReviewAction
from app.models.event import AuditEvent, ReviewDecision, WeatherEvent
from app.schemas.reviews import ReviewRequest
from sqlalchemy import case, select
from sqlalchemy.orm import Session, joinedload


class ReviewError(Exception):
    pass


class ReviewConflictError(ReviewError):
    pass


class ReviewService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def queue(self) -> list[WeatherEvent]:
        severity_rank = case((WeatherEvent.severity == "CRITICAL", 4), (WeatherEvent.severity == "HIGH", 3), (WeatherEvent.severity == "MODERATE", 2), else_=1)
        assessment_rank = case((WeatherEvent.system_assessment == SystemAssessment.DISPUTED, 2), (WeatherEvent.system_assessment == SystemAssessment.NEEDS_REVIEW, 1), else_=0)
        partial_rank = case((WeatherEvent.processing_status == ProcessingStatus.PARTIAL, 1), else_=0)
        return self.session.scalars(select(WeatherEvent).options(joinedload(WeatherEvent.source)).where(WeatherEvent.admin_status == AdminStatus.UNREVIEWED).order_by(severity_rank.desc(), assessment_rank.desc(), partial_rank.desc(), WeatherEvent.observed_at.desc())).unique().all()

    def get(self, event_id: UUID) -> WeatherEvent | None:
        return self.session.scalar(select(WeatherEvent).options(joinedload(WeatherEvent.source)).where(WeatherEvent.id == event_id))

    def audit(self, event_id: UUID) -> list[AuditEvent]:
        return self.session.scalars(select(AuditEvent).where(AuditEvent.event_id == event_id).order_by(AuditEvent.created_at.desc())).all()

    def attention_reason(self, event: WeatherEvent) -> str:
        signals = []
        if event.system_assessment in {SystemAssessment.NEEDS_REVIEW, SystemAssessment.DISPUTED}:
            signals.append(event.system_assessment.replace("_", " ").title())
        if event.processing_status == ProcessingStatus.PARTIAL:
            signals.append("partial processing")
        if event.severity in {"HIGH", "CRITICAL"}:
            signals.append(f"{event.severity.lower()} severity")
        return ", ".join(signals) or "unreviewed event"

    def decide(self, event_id: UUID, request: ReviewRequest) -> tuple[ReviewDecision, WeatherEvent]:
        target = {ReviewAction.VERIFY: AdminStatus.VERIFIED, ReviewAction.REJECT: AdminStatus.REJECTED, ReviewAction.ESCALATE: AdminStatus.ESCALATED}[request.action]
        with self.session.begin():
            event = self.session.scalar(select(WeatherEvent).where(WeatherEvent.id == event_id).with_for_update())
            if event is None:
                raise ReviewError("Event not found.")
            if event.version != request.expected_version:
                raise ReviewConflictError("This event changed after you opened it. Refresh before submitting a decision.")
            if event.admin_status != AdminStatus.UNREVIEWED:
                raise ReviewError("Only UNREVIEWED events can receive a decision.")
            previous = event.admin_status
            event.admin_status = target
            event.version += 1
            decision = ReviewDecision(event_id=event.id, action=request.action, previous_admin_status=previous, new_admin_status=target, reviewer_id=request.reviewer_id, reviewer_name=request.reviewer_name, reason=request.reason, notes=request.notes, event_version=event.version)
            audit = AuditEvent(event_id=event.id, event_type="WEATHER_EVENT", action=request.action, actor_type="HUMAN", actor_id=request.reviewer_id, actor_name=request.reviewer_name, previous_value=previous, new_value=target, reason=request.reason, metadata_={"review_decision": True, "event_version": event.version})
            self.session.add_all([decision, audit])
            self.session.flush()
        self.session.refresh(decision)
        self.session.refresh(event)
        return decision, event

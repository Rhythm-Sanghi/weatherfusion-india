from app.ingestion.contracts import NormalizedEventInput
from app.schemas.events import EventCreate


def normalize_event(payload: EventCreate) -> NormalizedEventInput:
    raw_text = payload.raw_text or payload.description or ""
    description = payload.description or raw_text
    title = payload.title or f"{payload.event_type.value.replace('_', ' ').title()} report"
    return NormalizedEventInput(
        source_name=payload.source,
        source_type=payload.source_type.upper(),
        external_id=payload.external_id or None,
        event_type=payload.event_type,
        severity=payload.severity.upper(),
        title=title,
        description=description,
        raw_text=raw_text,
        latitude=payload.latitude,
        longitude=payload.longitude,
        state=payload.state,
        district=payload.district,
        city=payload.city,
        observed_at=payload.observed_at,
        metadata=payload.metadata,
    )

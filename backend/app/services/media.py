from collections.abc import Iterable

from app.models.event import MediaEvidence, WeatherEvent
from app.schemas.citizen_reports import MediaEvidenceCreate
from sqlalchemy.orm import Session


def attach_media_evidence(
    session: Session,
    event: WeatherEvent,
    media: Iterable[MediaEvidenceCreate | dict[str, object]],
    *,
    source_name: str,
    is_demo: bool,
) -> None:
    for item in media:
        data = item.model_dump() if isinstance(item, MediaEvidenceCreate) else item
        session.add(
            MediaEvidence(
                event_id=event.id,
                media_type=str(data["media_type"]),
                reference=str(data["reference"]),
                mime_type=str(data["mime_type"]) if data.get("mime_type") else None,
                caption=str(data["caption"]) if data.get("caption") else None,
                source_name=source_name,
                is_demo=is_demo,
            )
        )
    session.commit()
    session.refresh(event)

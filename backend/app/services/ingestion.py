import logging
from dataclasses import replace
from typing import Any

from app.domain.events import ProcessingStatus, SystemAssessment
from app.domain.providers import (
    GeospatialEventInput,
    GeospatialProvider,
    VerificationContext,
    VerificationEventInput,
    VerificationProvider,
)
from app.ingestion.normalizer import normalize_event
from app.models.event import RawIngestRecord, WeatherEvent
from app.repositories.events import EventRepository
from app.schemas.events import EventCreate
from app.services.duplicate_candidates import retrieve_duplicate_candidates
from sqlalchemy.orm import Session

logger = logging.getLogger("weatherfusion.ingestion")


class DuplicateExternalIdError(Exception):
    pass


class IngestionService:
    def __init__(
        self,
        session: Session,
        verification_provider: VerificationProvider,
        geospatial_provider: GeospatialProvider,
    ) -> None:
        self.session = session
        self.repository = EventRepository(session)
        self.verification_provider = verification_provider
        self.geospatial_provider = geospatial_provider

    async def ingest(self, payload: EventCreate, raw_payload: dict[str, Any]) -> WeatherEvent:
        normalized = normalize_event(payload)
        source = self.repository.get_or_create_source(
            normalized.source_name, normalized.source_type
        )
        if self.repository.find_by_external_id(source.id, normalized.external_id):
            raise DuplicateExternalIdError(normalized.external_id or "")

        self.session.add(
            RawIngestRecord(
                source_id=source.id,
                external_id=normalized.external_id,
                raw_payload=raw_payload,
                validation_status="ACCEPTED",
            )
        )
        event = WeatherEvent(
            source_id=source.id,
            external_id=normalized.external_id,
            event_type=normalized.event_type,
            severity=normalized.severity,
            title=normalized.title,
            description=normalized.description,
            raw_text=normalized.raw_text,
            latitude=normalized.latitude,
            longitude=normalized.longitude,
            state=normalized.state,
            district=normalized.district,
            city=normalized.city,
            observed_at=normalized.observed_at,
            processing_status=ProcessingStatus.PROCESSING,
            metadata_=normalized.metadata.copy(),
        )
        self.session.add(event)
        self.session.flush()

        partial = await self._run_providers(event)
        event.processing_status = ProcessingStatus.PARTIAL if partial else ProcessingStatus.COMPLETE
        self.session.commit()
        return self.repository.get(event.id) or event

    async def _run_providers(self, event: WeatherEvent) -> bool:
        provider_status: dict[str, str] = {}
        machine_analysis: dict[str, object] = {}
        partial = False
        verification_input = VerificationEventInput(
            event_id=event.id,
            text=event.raw_text,
            event_type=event.event_type,
            observed_at=event.observed_at,
            latitude=event.latitude,
            longitude=event.longitude,
            source_type=event.source.source_type,
            metadata=event.metadata_,
        )
        try:
            classification = await self.verification_provider.classify(verification_input)
            machine_analysis["classification"] = {
                "event_type": classification.event_type.value,
                "confidence": classification.confidence,
                "provider": _metadata_dict(classification.metadata),
                "status": "AVAILABLE" if classification.details is not None else ("UNTRAINED" if classification.confidence is None else "AVAILABLE"),
                **(classification.details or {}),
            }
            provider_status["classification"] = machine_analysis["classification"]["status"]
        except Exception:
            logger.exception("classification_provider_unavailable event_id=%s", event.id)
            machine_analysis["classification"] = {"status": "UNAVAILABLE"}
            provider_status["classification"] = "UNAVAILABLE"

        try:
            candidates = retrieve_duplicate_candidates(
                self.session,
                event_id=event.id,
                latitude=event.latitude,
                longitude=event.longitude,
                observed_at=event.observed_at,
                event_type=event.event_type,
            )
            duplicates = await self.verification_provider.find_duplicates(
                verification_input, candidates
            )
            machine_analysis["duplicate_candidates"] = [
                {
                    "event_id": str(result.candidate_event_id),
                    "similarity": result.similarity,
                    "provider": _metadata_dict(result.metadata),
                }
                for result in duplicates
            ]
            provider_status["duplicate_detection"] = "AVAILABLE"
        except Exception:
            logger.exception("duplicate_detection_unavailable event_id=%s", event.id)
            machine_analysis["duplicate_candidates"] = {"status": "UNAVAILABLE"}
            provider_status["duplicate_detection"] = "UNAVAILABLE"
        try:
            verification_input = replace(
                verification_input, metadata={"machine_analysis": machine_analysis}
            )
            assessment = await self.verification_provider.evaluate(
                verification_input, VerificationContext()
            )
            event.system_assessment = assessment.assessment
            provider_status["verification"] = assessment.assessment.value
            machine_analysis["verification"] = {
                "assessment": assessment.assessment.value,
                "score": assessment.score,
                "reason_codes": list(assessment.reason_codes),
                "evidence_references": list(assessment.evidence_references),
                "provider": _metadata_dict(assessment.metadata),
                **({"evidence": assessment.evidence} if assessment.evidence is not None else {}),
            }
            partial = assessment.assessment is SystemAssessment.UNAVAILABLE
        except Exception:
            logger.exception("verification_provider_unavailable event_id=%s", event.id)
            event.system_assessment = SystemAssessment.UNAVAILABLE
            provider_status["verification"] = "UNAVAILABLE"
            machine_analysis["verification"] = {"status": "UNAVAILABLE"}
            partial = True

        if event.latitude is None or event.longitude is None:
            provider_status["geospatial"] = "SKIPPED_NO_COORDINATES"
            event.metadata_ = {
                **event.metadata_,
                "provider_status": provider_status,
                "machine_analysis": machine_analysis,
            }
            return partial
        geospatial_input = GeospatialEventInput(
            event_id=event.id,
            latitude=event.latitude,
            longitude=event.longitude,
            observed_at=event.observed_at,
            state=event.state,
            district=event.district,
            city=event.city,
        )
        try:
            enrichment = await self.geospatial_provider.enrich_location(geospatial_input)
            provider_status["geospatial"] = enrichment.status
        except Exception:
            logger.exception("geospatial_provider_unavailable event_id=%s", event.id)
            provider_status["geospatial"] = "UNAVAILABLE"
            partial = True
        event.metadata_ = {
            **event.metadata_,
            "provider_status": provider_status,
            "machine_analysis": machine_analysis,
        }
        return partial


def _metadata_dict(metadata: object) -> dict[str, str]:
    """Serialize provider provenance into the event's JSON metadata."""
    return {
        "provider_name": str(metadata.provider_name),
        "provider_version": str(metadata.provider_version),
        "generated_at": metadata.generated_at.isoformat(),
    }

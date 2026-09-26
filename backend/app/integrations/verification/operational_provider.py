"""Explainable local verification backed by persisted canonical reports."""
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.events import EventCategory, SystemAssessment
from app.domain.providers import (
    CandidateEvent,
    ClassificationResult,
    DuplicateResult,
    ProviderMetadata,
    VerificationContext,
    VerificationEventInput,
    VerificationProvider,
    VerificationResult,
)
from app.models.event import Source, WeatherEvent
from app.services.duplicate_ranking import rank_duplicate_candidates
from app.services.evidence_policy import EvidenceComponent, summarize


class OperationalVerificationProvider(VerificationProvider):
    """Use stored reports as attributable, limited evidence for review triage."""

    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()

    @staticmethod
    def _metadata() -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="operational-verification",
            provider_version="1.0",
            generated_at=datetime.now(UTC),
        )

    async def classify(self, event: VerificationEventInput) -> ClassificationResult:
        """Report no trained model without changing source-provided labels."""
        return ClassificationResult(EventCategory.UNKNOWN, None, self._metadata())

    async def find_duplicates(
        self, event: VerificationEventInput, candidates: Sequence[CandidateEvent]
    ) -> list[DuplicateResult]:
        return rank_duplicate_candidates(event, list(candidates), self._metadata())

    async def evaluate(
        self, event: VerificationEventInput, context: VerificationContext
    ) -> VerificationResult:
        metadata = self._metadata()
        components: list[EvidenceComponent] = [self._source_reliability(event)]
        corroboration, conflicting_references = self._independent_corroboration(event)
        components.append(corroboration)
        components.extend((
            self._official_observation(event),
            self._location_time_consistency(event),
            self._ml_evidence(event),
        ))
        evidence = summarize(tuple(components), method_version="evidence-ranking-v1")
        score = evidence["score"]
        coverage = evidence["coverage"]
        reason_codes = tuple(str(code) for code in evidence["reason_codes"])
        references = tuple(str(reference) for reference in evidence["evidence_references"])
        if conflicting_references:
            reason_codes = (*reason_codes, "CONFLICTING_NEARBY_EVENT_TYPES")
            references = (*references, *conflicting_references)
        assessment = SystemAssessment.NEEDS_REVIEW
        if score is None:
            reason_codes = (*reason_codes, "INSUFFICIENT_AVAILABLE_EVIDENCE")
        elif float(coverage) < self.settings.evidence_minimum_coverage:
            reason_codes = (*reason_codes, "INSUFFICIENT_EVIDENCE_COVERAGE")
        elif float(score) >= 0.70 and not conflicting_references:
            assessment = SystemAssessment.CORROBORATED
            reason_codes = (*reason_codes, "EVIDENCE_COVERAGE_AND_SCORE_THRESHOLD_MET")
        return VerificationResult(
            assessment,
            float(score) if score is not None else None,
            reason_codes,
            metadata,
            references,
            evidence,
        )

    def _source_reliability(self, event: VerificationEventInput) -> EvidenceComponent:
        row = self.session.execute(
            select(Source.reliability)
            .join(WeatherEvent, WeatherEvent.source_id == Source.id)
            .where(WeatherEvent.id == event.event_id)
        ).scalar_one_or_none()
        if row is None:
            return EvidenceComponent(
                "source_reliability",
                self.settings.evidence_source_reliability_weight,
                False,
                None,
                ("SOURCE_RELIABILITY_NOT_CONFIGURED",),
            )
        return EvidenceComponent(
            "source_reliability",
            self.settings.evidence_source_reliability_weight,
            True,
            max(0.0, min(1.0, float(row))),
            ("SOURCE_RELIABILITY_PROFILE",),
        )

    def _official_observation(self, event: VerificationEventInput) -> EvidenceComponent:
        """Compare with nearby Open-Meteo *observations*, never its forecast endpoint."""
        if event.latitude is None or event.longitude is None:
            return EvidenceComponent("official_weather_observations", self.settings.evidence_official_observation_weight, False, None, ("OFFICIAL_OBSERVATION_NO_COORDINATES",))
        if self.session.bind is None or self.session.bind.dialect.name != "postgresql":
            return EvidenceComponent("official_weather_observations", self.settings.evidence_official_observation_weight, False, None, ("OFFICIAL_OBSERVATION_REQUIRES_POSTGIS",))
        current_location = select(WeatherEvent.location).where(
            WeatherEvent.id == event.event_id
        ).scalar_subquery()
        candidates = self.session.execute(
            select(WeatherEvent.id, WeatherEvent.event_type)
            .select_from(WeatherEvent)
            .join(Source, Source.id == WeatherEvent.source_id)
            .where(
                Source.source_type == "EXTERNAL_WEATHER",
                WeatherEvent.id != event.event_id,
                WeatherEvent.observed_at.between(event.observed_at - timedelta(hours=3), event.observed_at + timedelta(hours=3)),
                WeatherEvent.location.is_not(None),
                func.ST_DWithin(WeatherEvent.location, current_location, self.settings.evidence_corroboration_radius_meters),
            )
            .limit(10)
        ).all()
        if not candidates:
            return EvidenceComponent("official_weather_observations", self.settings.evidence_official_observation_weight, False, None, ("OFFICIAL_OBSERVATION_NOT_AVAILABLE",))
        matching = [row for row in candidates if row.event_type is event.event_type]
        return EvidenceComponent(
            "official_weather_observations", self.settings.evidence_official_observation_weight,
            True, 1.0 if matching else 0.0,
            ("OFFICIAL_OBSERVATION_EVENT_TYPE_MATCH" if matching else "OFFICIAL_OBSERVATION_EVENT_TYPE_MISMATCH",),
            tuple(str(row.id) for row in candidates),
        )

    def _location_time_consistency(self, event: VerificationEventInput) -> EvidenceComponent:
        """Validate that the report contains plausible spatial and temporal fields.

        This is record-consistency evidence only; it does not validate that weather occurred.
        """
        if event.latitude is None or event.longitude is None:
            return EvidenceComponent("location_time_consistency", self.settings.evidence_location_time_weight, False, None, ("LOCATION_TIME_NO_COORDINATES",))
        now = datetime.now(UTC)
        observed = event.observed_at.astimezone(UTC)
        age = now - observed
        future = timedelta(minutes=self.settings.evidence_location_time_future_tolerance_minutes)
        maximum_age = timedelta(hours=self.settings.evidence_location_time_max_age_hours)
        plausible = -future <= age <= maximum_age
        return EvidenceComponent(
            "location_time_consistency", self.settings.evidence_location_time_weight, True,
            1.0 if plausible else 0.0,
            ("LOCATION_TIME_FIELDS_PLAUSIBLE" if plausible else "LOCATION_TIME_FIELDS_IMPLAUSIBLE",),
        )

    def _ml_evidence(self, event: VerificationEventInput) -> EvidenceComponent:
        analysis = (event.metadata or {}).get("machine_analysis")
        classification = analysis.get("classification") if isinstance(analysis, dict) else None
        if not isinstance(classification, dict) or classification.get("status") != "AVAILABLE":
            return EvidenceComponent("validated_ml_evidence", self.settings.evidence_validated_ml_weight, False, None, ("VALIDATED_ML_EVIDENCE_NOT_AVAILABLE",))
        predicted = classification.get("event_type")
        value = 1.0 if predicted == event.event_type.value else 0.0
        return EvidenceComponent("validated_ml_evidence", self.settings.evidence_validated_ml_weight, True, value, ("ML_EVENT_TYPE_MATCH" if value else "ML_EVENT_TYPE_MISMATCH",))

    def _independent_corroboration(
        self, event: VerificationEventInput
    ) -> tuple[EvidenceComponent, tuple[str, ...]]:
        if event.latitude is None or event.longitude is None:
            return (
                EvidenceComponent(
                    "independent_corroboration",
                    self.settings.evidence_independent_corroboration_weight,
                    False,
                    None,
                    ("INDEPENDENT_CORROBORATION_NO_COORDINATES",),
                ),
                (),
            )
        if event.event_type is EventCategory.UNKNOWN:
            return (
                EvidenceComponent(
                    "independent_corroboration",
                    self.settings.evidence_independent_corroboration_weight,
                    False,
                    None,
                    ("INDEPENDENT_CORROBORATION_UNKNOWN_EVENT_TYPE",),
                ),
                (),
            )
        current = select(WeatherEvent.location, WeatherEvent.source_id).where(
            WeatherEvent.id == event.event_id
        ).subquery()
        rows = list(
            self.session.execute(
                select(WeatherEvent.id, WeatherEvent.event_type, WeatherEvent.source_id)
                .where(
                    WeatherEvent.id != event.event_id,
                    WeatherEvent.source_id != current.c.source_id,
                    WeatherEvent.location.is_not(None),
                    WeatherEvent.observed_at.between(
                        event.observed_at - timedelta(hours=self.settings.evidence_corroboration_window_hours),
                        event.observed_at + timedelta(hours=self.settings.evidence_corroboration_window_hours),
                    ),
                    func.ST_DWithin(
                        WeatherEvent.location,
                        current.c.location,
                        self.settings.evidence_corroboration_radius_meters,
                    ),
                )
                .order_by(WeatherEvent.observed_at.desc(), WeatherEvent.id)
                .limit(50)
            )
        )
        supporting = [row for row in rows if row.event_type is event.event_type]
        distinct_sources = {row.source_id for row in supporting}
        value = min(1.0, len(distinct_sources) / self.settings.evidence_corroboration_sources_for_full_support)
        supporting_references = tuple(str(row.id) for row in supporting)
        conflicting_references = tuple(str(row.id) for row in rows if row.event_type is not event.event_type)
        reason = (
            "INDEPENDENT_NEARBY_SOURCES_SUPPORT_EVENT_TYPE"
            if distinct_sources
            else "NO_INDEPENDENT_NEARBY_SOURCE_SUPPORT"
        )
        return (
            EvidenceComponent(
                "independent_corroboration",
                self.settings.evidence_independent_corroboration_weight,
                True,
                value,
                (reason,),
                supporting_references,
            ),
            conflicting_references,
        )

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.events import EventCategory, SystemAssessment


@dataclass(frozen=True, slots=True)
class ProviderMetadata:
    provider_name: str
    provider_version: str
    generated_at: datetime


@dataclass(frozen=True, slots=True)
class VerificationEventInput:
    event_id: UUID
    text: str
    event_type: EventCategory
    observed_at: datetime
    latitude: float | None = None
    longitude: float | None = None
    source_type: str | None = None


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    event_type: EventCategory
    confidence: float | None
    metadata: ProviderMetadata


@dataclass(frozen=True, slots=True)
class VerificationContext:
    available_signals: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class VerificationResult:
    assessment: SystemAssessment
    score: float | None
    reason_codes: tuple[str, ...]
    metadata: ProviderMetadata


@dataclass(frozen=True, slots=True)
class CandidateEvent:
    event_id: UUID
    text: str
    observed_at: datetime
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True, slots=True)
class DuplicateResult:
    candidate_event_id: UUID
    similarity: float | None
    metadata: ProviderMetadata


class VerificationProvider(Protocol):
    async def classify(self, event: VerificationEventInput) -> ClassificationResult: ...

    async def evaluate(
        self, event: VerificationEventInput, context: VerificationContext
    ) -> VerificationResult: ...

    async def find_duplicates(
        self, event: VerificationEventInput, candidates: Sequence[CandidateEvent]
    ) -> list[DuplicateResult]: ...


@dataclass(frozen=True, slots=True)
class GeospatialEventInput:
    event_id: UUID
    latitude: float
    longitude: float
    observed_at: datetime
    state: str | None = None
    district: str | None = None
    city: str | None = None


@dataclass(frozen=True, slots=True)
class LocationEnrichment:
    state: str | None
    district: str | None
    city: str | None
    status: str
    metadata: ProviderMetadata


@dataclass(frozen=True, slots=True)
class NearbyQuery:
    radius_km: float
    observed_after: datetime | None = None


@dataclass(frozen=True, slots=True)
class NearbyEvent:
    event_id: UUID
    relationship: str
    distance_km: float | None
    metadata: ProviderMetadata


@dataclass(frozen=True, slots=True)
class RegionSummaryFilters:
    state: str | None = None
    event_type: EventCategory | None = None
    observed_after: datetime | None = None


@dataclass(frozen=True, slots=True)
class RegionSummary:
    region_id: str
    region_name: str
    event_count: int
    metadata: ProviderMetadata


class GeospatialProvider(Protocol):
    async def enrich_location(self, event: GeospatialEventInput) -> LocationEnrichment: ...

    async def find_nearby(
        self, event: GeospatialEventInput, query: NearbyQuery
    ) -> list[NearbyEvent]: ...

    async def region_summary(self, filters: RegionSummaryFilters) -> list[RegionSummary]: ...

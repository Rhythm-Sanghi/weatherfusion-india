from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.domain.events import EventCategory, ProcessingStatus, SystemAssessment
from app.domain.reviews import AdminStatus


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
    metadata: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    event_type: EventCategory
    confidence: float | None
    metadata: ProviderMetadata
    details: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class VerificationContext:
    available_signals: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class VerificationResult:
    assessment: SystemAssessment
    score: float | None
    reason_codes: tuple[str, ...]
    metadata: ProviderMetadata
    evidence_references: tuple[str, ...] = ()
    evidence: dict[str, object] | None = None


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
    radius_meters: float = 5_000
    radius_km: float | None = None
    limit: int = 20
    observed_after: datetime | None = None
    observed_before: datetime | None = None
    event_type: EventCategory | None = None
    severity: str | None = None
    processing_status: ProcessingStatus | None = None
    system_assessment: SystemAssessment | None = None
    admin_status: AdminStatus | None = None
    source_type: str | None = None

    def __post_init__(self) -> None:
        if self.radius_km is not None:
            object.__setattr__(self, "radius_meters", self.radius_km * 1_000)


@dataclass(frozen=True, slots=True)
class NearbyEvent:
    event_id: UUID
    relationship: str
    distance_meters: float | None
    observed_at: datetime | None
    title: str | None
    event_type: EventCategory | None
    source_name: str | None
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


class RegionalGroupingMethod(StrEnum):
    SOURCE_PROVIDED_LOCATION = "SOURCE_PROVIDED_LOCATION"
    BOUNDARY_DERIVED_LOCATION = "BOUNDARY_DERIVED_LOCATION"


@dataclass(frozen=True, slots=True)
class MapEventFilters:
    event_type: EventCategory | None = None
    severity: str | None = None
    processing_status: ProcessingStatus | None = None
    system_assessment: SystemAssessment | None = None
    admin_status: AdminStatus | None = None
    source_type: str | None = None
    observed_after: datetime | None = None
    observed_before: datetime | None = None
    boundary_id: UUID | None = None
    limit: int = 500


@dataclass(frozen=True, slots=True)
class GeographicAggregationFilters(MapEventFilters):
    state: str | None = None
    district: str | None = None


@dataclass(frozen=True, slots=True)
class ClusterQuery:
    filters: GeographicAggregationFilters
    distance_meters: float = 20_000
    min_points: int = 2
    limit: int = 100


@dataclass(frozen=True, slots=True)
class HotspotQuery:
    filters: GeographicAggregationFilters
    cell_size_meters: float = 25_000
    limit: int = 200


class GeospatialProvider(Protocol):
    async def enrich_location(self, event: GeospatialEventInput) -> LocationEnrichment: ...

    async def find_nearby(
        self, event: GeospatialEventInput, query: NearbyQuery
    ) -> list[NearbyEvent]: ...

    async def region_summary(self, filters: RegionSummaryFilters) -> list[RegionSummary]: ...

    async def geojson_features(self, filters: MapEventFilters) -> list[dict[str, object]]: ...

    async def clusters(self, query: ClusterQuery) -> list[dict[str, object]]: ...

    async def hotspots(self, query: HotspotQuery) -> list[dict[str, object]]: ...

    async def regional_summary(
        self, filters: GeographicAggregationFilters
    ) -> list[dict[str, object]]: ...

    async def boundary_regional_summary(
        self, filters: GeographicAggregationFilters, administrative_level: str
    ) -> dict[str, object]: ...

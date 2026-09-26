# Integration Contracts

These contracts are the Phase 1 boundary for teammate-owned modules. Provider DTOs are Python domain dataclasses and must not depend on FastAPI, SQLAlchemy, database models, or frontend types.

## Verification provider

`VerificationProvider` exposes three async methods:

```python
class VerificationProvider(Protocol):
    async def classify(self, event: VerificationEventInput) -> ClassificationResult: ...
    async def evaluate(self, event: VerificationEventInput, context: VerificationContext) -> VerificationResult: ...
    async def find_duplicates(
        self, event: VerificationEventInput, candidates: Sequence[CandidateEvent]
    ) -> list[DuplicateResult]: ...
```

`VerificationEventInput` contains a stable event ID, normalized text, event category, observed time, optional coordinates, and source type. `ClassificationResult` returns an event category, optional confidence in the range `0..1`, and `ProviderMetadata`. `VerificationResult` returns a `SystemAssessment`, optional score in `0..1`, explainable reason codes, and metadata. `DuplicateResult` identifies a candidate event and optional similarity in `0..1`.

Providers must be asynchronous, deterministic for test fixtures where practical, and versioned through `ProviderMetadata`. They must raise a clear integration exception for unrecoverable failures; later orchestration will persist the event and translate the failure into a pending or unavailable assessment. A provider must never set `AdminStatus.VERIFIED`.

The current `MockVerificationProvider` returns `UNKNOWN`, `UNAVAILABLE`, no score, and no duplicate candidates. It is a wiring placeholder, not a classifier or scoring implementation. Phase 2 safely calls `evaluate` only after canonical event persistence; an unavailable result or exception does not roll back ingestion.

## Geospatial provider

`GeospatialProvider` exposes read-only enrichment, candidate retrieval, regional summary,
and map-feature methods:

```python
class GeospatialProvider(Protocol):
    async def enrich_location(self, event: GeospatialEventInput) -> LocationEnrichment: ...
    async def find_nearby(self, event: GeospatialEventInput, query: NearbyQuery) -> list[NearbyEvent]: ...
    async def region_summary(self, filters: RegionSummaryFilters) -> list[RegionSummary]: ...
    async def geojson_features(self, filters: MapEventFilters) -> list[dict[str, object]]: ...
```

`GeospatialEventInput` contains stable event ID, latitude, longitude, observed time, and optional administrative names. `LocationEnrichment` returns optional state, district, and city plus a provider status. `NearbyQuery` includes a requested radius and optional time bound; `NearbyEvent` references an existing event and may include a provider-calculated distance. `RegionSummary` contains a stable region ID, name, event count, and metadata.

Coordinates are decimal degrees. `NearbyQuery.radius_meters` is expressed in metres; the
legacy `radius_km` input remains accepted for older contract consumers. The PostGIS provider
uses the request or ingestion session after its event flush, never commits, rolls back, or
closes that session. It uses `ST_DWithin` and `ST_Distance` against generated geography
points, and returns deterministic distance/ID ordering. A frontend consumes the backend
GeoJSON rather than calculating geographic distances itself. The mock provider remains an
empty, isolated-test implementation. Phase 2 calls enrichment only when coordinates are
present; a provider failure leaves the event persisted and marked partial.

## Integration expectations

Future implementations are selected through `VERIFICATION_PROVIDER` and `GEOSPATIAL_PROVIDER`. The factory functions in `app.api.dependencies` are the only composition point. Teammates should add a provider implementation, register its configuration name, and satisfy contract tests for type shape, score bounds, metadata, empty results, and failure behavior.

## G3 geographic aggregation

The PostGIS provider also supports typed cluster, hotspot, and regional-summary query DTOs.
Cluster IDs are scoped to a single query and are not persistent identities. A hotspot is a count
of submitted reports in a fixed spatial cell, not a forecast, severity score, or verification
result. Regional summaries can use source-provided attributes or the imported approved-boundary
dataset; the response identifies the grouping method, dataset, and vintage. `GET /api/v1/geo/boundaries`
returns the available boundary metadata and geometry for the selected level.
# Phase 6 teammate handoff

## AI/ML teammate

Implement a provider in `backend/app/integrations/verification/` matching `VerificationProvider` in `app.domain.providers`: `classify(VerificationEventInput)`, `evaluate(VerificationEventInput, VerificationContext)`, and `find_duplicates(VerificationEventInput, Sequence[CandidateEvent])`. Return the domain DTOs and shared enums only; do not mutate database, review state, or HTTP objects. Scores/confidence must be 0–1. Raise clear exceptions for timeouts/unavailability. Expose `ProviderMetadata` with name/version. Add factory support only when the module exists; `VERIFICATION_PROVIDER=teammate` must fail clearly until then. Run `pytest tests/test_provider_contracts.py`.

## Geospatial teammate

Implement a provider in `backend/app/integrations/geospatial/` matching `GeospatialProvider`: `enrich_location(GeospatialEventInput)`, `find_nearby(GeospatialEventInput, NearbyQuery)`, and `region_summary(RegionSummaryFilters)`. Inputs/outputs are domain DTOs; preserve valid coordinates, stable IDs, metadata, and explicit failure behavior. Do not mutate human-review state. Add factory support only when available; `GEOSPATIAL_PROVIDER=teammate` must fail clearly until then. Run `pytest tests/test_provider_contracts.py`.

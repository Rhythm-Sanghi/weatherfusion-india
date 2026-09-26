from datetime import UTC, datetime

from app.domain.providers import (
    ClusterQuery,
    GeographicAggregationFilters,
    GeospatialEventInput,
    GeospatialProvider,
    HotspotQuery,
    LocationEnrichment,
    MapEventFilters,
    NearbyEvent,
    NearbyQuery,
    ProviderMetadata,
    RegionSummary,
    RegionSummaryFilters,
)


class MockGeospatialProvider(GeospatialProvider):
    """Deliberately non-geospatial Phase 1 integration placeholder."""

    @staticmethod
    def _metadata() -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="mock-geospatial",
            provider_version="phase-1",
            generated_at=datetime.now(UTC),
        )

    async def enrich_location(self, event: GeospatialEventInput) -> LocationEnrichment:
        return LocationEnrichment(None, None, None, "PENDING", self._metadata())

    async def find_nearby(
        self, event: GeospatialEventInput, query: NearbyQuery
    ) -> list[NearbyEvent]:
        return []

    async def region_summary(self, filters: RegionSummaryFilters) -> list[RegionSummary]:
        return []

    async def geojson_features(self, filters: MapEventFilters) -> list[dict[str, object]]:
        return []

    async def clusters(self, query: ClusterQuery) -> list[dict[str, object]]:
        return []

    async def hotspots(self, query: HotspotQuery) -> list[dict[str, object]]:
        return []

    async def regional_summary(
        self, filters: GeographicAggregationFilters
    ) -> list[dict[str, object]]:
        return []

    async def boundary_regional_summary(
        self, filters: GeographicAggregationFilters, administrative_level: str
    ) -> dict[str, object]:
        return {
            "administrative_level": administrative_level,
            "grouping_method": "BOUNDARY_DERIVED_LOCATION",
            "regions": [],
            "categories": {"AMBIGUOUS": 0, "UNMATCHED": 0, "NO_COORDINATES": 0},
            "filtered_event_count": 0,
            "applied_observation_time_range": {
                "from": filters.observed_after,
                "to": filters.observed_before,
            },
            "coverage_note": "Mock geospatial provider has no boundary data.",
        }

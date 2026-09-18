from datetime import UTC, datetime

from app.domain.providers import (
    GeospatialEventInput,
    GeospatialProvider,
    LocationEnrichment,
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

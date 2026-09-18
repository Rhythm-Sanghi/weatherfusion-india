from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.domain.events import EventCategory, SystemAssessment
from app.domain.providers import (
    CandidateEvent,
    GeospatialEventInput,
    NearbyQuery,
    RegionSummaryFilters,
    VerificationContext,
    VerificationEventInput,
)
from app.integrations.geospatial.mock_provider import MockGeospatialProvider
from app.integrations.verification.mock_provider import MockVerificationProvider


@pytest.mark.asyncio
async def test_verification_provider_contract() -> None:
    event = VerificationEventInput(uuid4(), "fixture", EventCategory.FLOOD, datetime.now(UTC))
    provider = MockVerificationProvider()
    classification = await provider.classify(event)
    result = await provider.evaluate(event, VerificationContext())
    duplicates = await provider.find_duplicates(event, [CandidateEvent(uuid4(), "candidate", datetime.now(UTC))])
    assert isinstance(classification.event_type, EventCategory)
    assert classification.confidence is None or 0 <= classification.confidence <= 1
    assert isinstance(result.assessment, SystemAssessment)
    assert result.score is None or 0 <= result.score <= 1
    assert all(item.candidate_event_id for item in duplicates)


@pytest.mark.asyncio
async def test_geospatial_provider_contract() -> None:
    event = GeospatialEventInput(uuid4(), 19.076, 72.8777, datetime.now(UTC))
    provider = MockGeospatialProvider()
    location = await provider.enrich_location(event)
    nearby = await provider.find_nearby(event, NearbyQuery(radius_km=1))
    summary = await provider.region_summary(RegionSummaryFilters())
    assert location.status == "PENDING"
    assert nearby == []
    assert summary == []

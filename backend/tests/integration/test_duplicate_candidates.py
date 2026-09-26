import asyncio
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.domain.events import EventCategory, ProcessingStatus, SystemAssessment
from app.domain.providers import VerificationContext, VerificationEventInput
from app.domain.reviews import AdminStatus
from app.integrations.verification.operational_provider import OperationalVerificationProvider
from app.models.event import Source
from app.services.duplicate_candidates import retrieve_duplicate_candidates
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

POSTGIS_TEST_DATABASE_URL = os.getenv("POSTGIS_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not POSTGIS_TEST_DATABASE_URL,
    reason="POSTGIS_TEST_DATABASE_URL is required for PostGIS integration tests",
)


@pytest.fixture
def session() -> Session:
    assert POSTGIS_TEST_DATABASE_URL
    engine = create_engine(POSTGIS_TEST_DATABASE_URL)
    connection = engine.connect()
    transaction = connection.begin()
    database_session = Session(bind=connection)
    try:
        yield database_session
    finally:
        database_session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


def _source_id(session: Session):
    source_id = session.scalar(text("SELECT id FROM sources ORDER BY id LIMIT 1"))
    assert source_id is not None
    return source_id


def _insert_event(
    session: Session,
    source_id: object,
    event_id: object,
    longitude: float | None,
    observed_at: datetime,
    event_type: EventCategory = EventCategory.HEAVY_RAINFALL,
    *,
    latitude: float | None = 28.0,
) -> None:
    session.execute(
        text(
            """
            INSERT INTO weather_events (
                id, source_id, event_type, severity, title, raw_text, latitude,
                longitude, observed_at, processing_status, system_assessment,
                admin_status, version, metadata
            ) VALUES (
                CAST(:id AS uuid), CAST(:source_id AS uuid), :event_type, 'HIGH',
                :title, 'PostGIS duplicate fixture', :latitude, :longitude,
                :observed_at, :processing_status, :system_assessment, :admin_status, 1,
                CAST('{}' AS json)
            )
            """
        ),
        {
            "id": str(event_id),
            "source_id": str(source_id),
            "event_type": event_type.value,
            "title": f"Duplicate fixture {event_id}",
            "latitude": latitude,
            "longitude": longitude,
            "observed_at": observed_at,
            "processing_status": ProcessingStatus.COMPLETE.value,
            "system_assessment": SystemAssessment.NEEDS_REVIEW.value,
            "admin_status": AdminStatus.UNREVIEWED.value,
        },
    )


def test_retrieval_uses_postgis_radius_time_type_limit_and_stable_order(session: Session) -> None:
    source_id = _source_id(session)
    observed_at = datetime(2026, 9, 20, 12, tzinfo=UTC)
    current_id, near_first_id, near_second_id, far_id, old_id, other_type_id = (
        uuid4() for _ in range(6)
    )
    _insert_event(session, source_id, current_id, 77.0, observed_at, latitude=28.0)
    # About 390 m east: within the 500 m radius.
    _insert_event(session, source_id, near_first_id, 77.004, observed_at, latitude=28.0)
    _insert_event(session, source_id, near_second_id, 77.003, observed_at, latitude=28.0)
    _insert_event(session, source_id, far_id, 77.02, observed_at, latitude=28.0)
    _insert_event(session, source_id, old_id, 77.003, observed_at - timedelta(hours=25), latitude=28.0)
    _insert_event(
        session,
        source_id,
        other_type_id,
        77.003,
        observed_at,
        EventCategory.FLOOD,
        latitude=28.0,
    )
    session.flush()

    candidates = retrieve_duplicate_candidates(
        session,
        event_id=current_id,
        latitude=28.0,
        longitude=77.0,
        observed_at=observed_at,
        event_type=EventCategory.HEAVY_RAINFALL,
        radius_meters=500,
        time_window_hours=24,
        limit=10,
    )
    expected_ids = sorted([near_first_id, near_second_id], key=str)
    assert [candidate.event_id for candidate in candidates] == expected_ids
    assert all(candidate.latitude == 28.0 for candidate in candidates)
    assert all(candidate.longitude is not None for candidate in candidates)

    limited = retrieve_duplicate_candidates(
        session,
        event_id=current_id,
        latitude=28.0,
        longitude=77.0,
        observed_at=observed_at,
        event_type=EventCategory.HEAVY_RAINFALL,
        radius_meters=500,
        time_window_hours=24,
        limit=1,
    )
    assert len(limited) == 1
    assert limited[0].event_id == expected_ids[0]


def test_retrieval_is_read_only_and_requires_coordinates_and_time(session: Session) -> None:
    source_id = _source_id(session)
    observed_at = datetime(2026, 9, 20, 12, tzinfo=UTC)
    current_id, nearby_id = uuid4(), uuid4()
    _insert_event(session, source_id, current_id, 77.0, observed_at, latitude=28.0)
    _insert_event(session, source_id, nearby_id, 77.001, observed_at, latitude=28.0)
    session.flush()
    before = session.scalar(text("SELECT count(*) FROM weather_events"))

    assert retrieve_duplicate_candidates(
        session,
        event_id=current_id,
        latitude=None,
        longitude=77.0,
        observed_at=observed_at,
        event_type=EventCategory.HEAVY_RAINFALL,
    ) == []
    assert retrieve_duplicate_candidates(
        session,
        event_id=current_id,
        latitude=28.0,
        longitude=77.0,
        observed_at=None,
        event_type=EventCategory.HEAVY_RAINFALL,
    ) == []
    candidates = retrieve_duplicate_candidates(
        session,
        event_id=current_id,
        latitude=28.0,
        longitude=77.0,
        observed_at=observed_at,
        event_type=EventCategory.UNKNOWN,
        radius_meters=500,
    )
    assert [candidate.event_id for candidate in candidates] == [nearby_id]
    assert session.scalar(text("SELECT count(*) FROM weather_events")) == before
    assert session.in_transaction()


def test_operational_provider_ranks_candidates_and_uses_independent_evidence(
    session: Session,
) -> None:
    source_id = _source_id(session)
    independent_source = Source(
        name=f"Independent duplicate fixture {uuid4()}", source_type="SOCIAL"
    )
    session.add(independent_source)
    session.flush()
    observed_at = datetime(2026, 9, 20, 12, tzinfo=UTC)
    current_id, same_source_id, independent_id = uuid4(), uuid4(), uuid4()
    _insert_event(session, source_id, current_id, 77.0, observed_at, latitude=28.0)
    _insert_event(session, source_id, same_source_id, 77.001, observed_at, latitude=28.0)
    _insert_event(
        session, independent_source.id, independent_id, 77.002, observed_at, latitude=28.0
    )
    session.flush()
    event = VerificationEventInput(
        current_id,
        "intense rainfall in Delhi",
        EventCategory.HEAVY_RAINFALL,
        observed_at,
        28.0,
        77.0,
        "CITIZEN",
    )
    candidates = retrieve_duplicate_candidates(
        session,
        event_id=current_id,
        latitude=28.0,
        longitude=77.0,
        observed_at=observed_at,
        event_type=EventCategory.HEAVY_RAINFALL,
        radius_meters=500,
    )
    provider = OperationalVerificationProvider(session)
    duplicates = asyncio.run(provider.find_duplicates(event, candidates))
    assessment = asyncio.run(provider.evaluate(event, VerificationContext()))
    assert {result.candidate_event_id for result in duplicates} == {same_source_id, independent_id}
    assert assessment.assessment is SystemAssessment.CORROBORATED
    assert "INDEPENDENT_NEARBY_SOURCES_SUPPORT_EVENT_TYPE" in assessment.reason_codes
    assert "EVIDENCE_COVERAGE_AND_SCORE_THRESHOLD_MET" in assessment.reason_codes
    assert str(independent_id) in assessment.evidence_references

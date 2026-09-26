import asyncio
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.api.dependencies import get_geospatial_provider
from app.core.config import Settings
from app.db import get_db_session
from app.domain.events import EventCategory, ProcessingStatus, SystemAssessment
from app.domain.providers import (
    ClusterQuery,
    GeographicAggregationFilters,
    GeospatialEventInput,
    HotspotQuery,
    MapEventFilters,
    NearbyQuery,
)
from app.domain.reviews import AdminStatus
from app.integrations.geospatial.postgis_provider import PostgisGeospatialProvider
from app.main import create_app
from app.repositories.events import EventRepository
from fastapi.testclient import TestClient
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


def _insert_event(
    session: Session,
    source_id: object,
    event_id: object,
    longitude: float | None,
    observed_at: datetime,
    event_type: EventCategory = EventCategory.HEAVY_RAINFALL,
    *,
    latitude: float | None = 28.0,
    processing_status: ProcessingStatus = ProcessingStatus.COMPLETE,
    system_assessment: SystemAssessment = SystemAssessment.NEEDS_REVIEW,
    admin_status: AdminStatus = AdminStatus.UNREVIEWED,
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
                :title, 'PostGIS integration fixture', :latitude, :longitude,
                :observed_at, :processing_status, :system_assessment, :admin_status, 1,
                CAST('{}' AS json)
            )
            """
        ),
        {
            "id": str(event_id),
            "source_id": str(source_id),
            "event_type": event_type.value,
            "title": f"Spatial fixture {event_id}",
            "latitude": latitude,
            "longitude": longitude,
            "observed_at": observed_at,
            "processing_status": processing_status.value,
            "system_assessment": system_assessment.value,
            "admin_status": admin_status.value,
        },
    )


def _boundary_point(session: Session, level: str, *, excluded_id: object | None = None) -> dict:
    exclusion = "" if excluded_id is None else "AND id <> CAST(:excluded_id AS uuid)"
    row = session.execute(
        text(
            """SELECT id, name, ST_X(ST_PointOnSurface(geometry)) AS longitude,
                      ST_Y(ST_PointOnSurface(geometry)) AS latitude
               FROM administrative_boundaries
               WHERE administrative_level = :level
                 """
            + exclusion
            + """
               ORDER BY name LIMIT 1"""
        ),
        {"level": level, "excluded_id": str(excluded_id)} if excluded_id else {"level": level},
    ).mappings().one()
    return dict(row)


def _boundary_test_client(session: Session) -> TestClient:
    assert POSTGIS_TEST_DATABASE_URL
    app = create_app(
        Settings(
            app_env="test",
            database_url=POSTGIS_TEST_DATABASE_URL,
            geospatial_provider="postgis",
        )
    )
    app.dependency_overrides[get_db_session] = lambda: session
    app.dependency_overrides[get_geospatial_provider] = lambda: PostgisGeospatialProvider(session)
    return TestClient(app)


def test_postgis_nearby_distance_filters_geojson_and_index(session: Session) -> None:
    source_id = session.scalar(text("SELECT id FROM sources ORDER BY id LIMIT 1"))
    assert source_id is not None
    observed_at = datetime(2026, 9, 19, 12, tzinfo=UTC)
    source_event_id, nearest_id, next_id, far_id = (uuid4() for _ in range(4))
    _insert_event(session, source_id, source_event_id, 77.0000, observed_at)
    _insert_event(session, source_id, nearest_id, 77.0040, observed_at)
    _insert_event(session, source_id, next_id, 77.0080, observed_at)
    _insert_event(
        session,
        source_id,
        far_id,
        77.0200,
        observed_at + timedelta(hours=2),
        EventCategory.FLOOD,
    )
    session.flush()

    provider = PostgisGeospatialProvider(session)
    event = GeospatialEventInput(source_event_id, 28.0, 77.0, observed_at)
    nearby = asyncio.run(
        provider.find_nearby(
            event,
            NearbyQuery(radius_meters=1_000, limit=10),
        )
    )
    assert [candidate.event_id for candidate in nearby] == [nearest_id, next_id]
    assert all(candidate.event_id != source_event_id for candidate in nearby)
    assert 300 < nearby[0].distance_meters < 500
    assert nearby[0].distance_meters < nearby[1].distance_meters

    filtered = asyncio.run(
        provider.find_nearby(
            event,
            NearbyQuery(
                radius_meters=1_000,
                event_type=EventCategory.FLOOD,
                observed_after=observed_at + timedelta(minutes=1),
            ),
        )
    )
    assert filtered == []

    features = asyncio.run(
        provider.geojson_features(
            MapEventFilters(
                event_type=EventCategory.HEAVY_RAINFALL,
                processing_status=ProcessingStatus.COMPLETE,
                system_assessment=SystemAssessment.NEEDS_REVIEW,
                admin_status=AdminStatus.UNREVIEWED,
            )
        )
    )
    source_feature = next(
        feature for feature in features if feature["properties"]["id"] == str(source_event_id)
    )
    assert source_feature["geometry"]["coordinates"] == [77.0, 28.0]

    aggregation_filters = GeographicAggregationFilters(
        event_type=EventCategory.HEAVY_RAINFALL,
        observed_after=observed_at - timedelta(minutes=1),
        observed_before=observed_at + timedelta(minutes=1),
    )
    clusters = asyncio.run(
        provider.clusters(
            ClusterQuery(aggregation_filters, distance_meters=1_000, min_points=2)
        )
    )
    assert len(clusters) == 1
    assert clusters[0]["event_ids"] == sorted(
        [str(nearest_id), str(next_id), str(source_event_id)]
    )
    assert clusters[0]["method"].startswith("ST_ClusterDBSCAN")

    hotspots = asyncio.run(provider.hotspots(HotspotQuery(aggregation_filters, 5_000)))
    assert sum(cell["event_count"] for cell in hotspots) == 3
    assert all(cell["method"] == "EPSG:6933 fixed metre grid" for cell in hotspots)

    session.execute(text("SET LOCAL enable_seqscan = off"))
    plan = "\n".join(
        session.scalars(
            text(
                """
                EXPLAIN SELECT id FROM weather_events
                WHERE ST_DWithin(
                    location,
                    ST_SetSRID(ST_MakePoint(77.0, 28.0), 4326)::geography,
                    1000
                )
                """
            )
        ).all()
    )
    assert "ix_weather_events_location_gist" in plan


def test_boundary_filters_use_imported_polygons_before_pagination(session: Session) -> None:
    """Exercise both API paths against the imported ADM1/ADM2 geometries."""
    source_id = session.scalar(text("SELECT id FROM sources ORDER BY id LIMIT 1"))
    assert source_id is not None
    adm1 = _boundary_point(session, "ADM1")
    other_adm1 = _boundary_point(session, "ADM1", excluded_id=adm1["id"])
    adm2 = _boundary_point(session, "ADM2")
    lakshadweep = session.execute(
        text(
            """SELECT id, ST_X(ST_PointOnSurface(geometry)) AS longitude,
                      ST_Y(ST_PointOnSurface(geometry)) AS latitude
               FROM administrative_boundaries
               WHERE administrative_level = 'ADM2' AND name ILIKE '%Lakshadweep%'"""
        )
    ).mappings().one()
    observed_at = datetime(2026, 9, 20, 12, tzinfo=UTC)
    matching_ids = [uuid4(), uuid4()]
    adm2_id, outside_id, null_id, lakshadweep_id = (uuid4() for _ in range(4))
    for index, event_id in enumerate(matching_ids):
        _insert_event(
            session,
            source_id,
            event_id,
            float(adm1["longitude"]),
            observed_at + timedelta(minutes=index),
            EventCategory.FLOOD,
            latitude=float(adm1["latitude"]),
        )
    _insert_event(
        session,
        source_id,
        adm2_id,
        float(adm2["longitude"]),
        observed_at,
        EventCategory.FLOOD,
        latitude=float(adm2["latitude"]),
    )
    _insert_event(
        session,
        source_id,
        outside_id,
        float(other_adm1["longitude"]),
        observed_at,
        EventCategory.FLOOD,
        latitude=float(other_adm1["latitude"]),
    )
    _insert_event(
        session,
        source_id,
        null_id,
        None,
        observed_at,
        EventCategory.FLOOD,
        latitude=None,
    )
    _insert_event(
        session,
        source_id,
        lakshadweep_id,
        float(lakshadweep["longitude"]),
        observed_at,
        EventCategory.FLOOD,
        latitude=float(lakshadweep["latitude"]),
    )
    session.flush()

    events, total = EventRepository(session).list(
        page=1,
        page_size=1,
        event_type=EventCategory.FLOOD,
        processing_status=ProcessingStatus.COMPLETE,
        boundary_id=adm1["id"],
        date_from=observed_at - timedelta(minutes=1),
        date_to=observed_at + timedelta(minutes=2),
    )
    assert total == 2
    assert len(events) == 1
    assert {event.id for event in events}.issubset(set(matching_ids))

    provider = PostgisGeospatialProvider(session)
    adm1_features = asyncio.run(
        provider.geojson_features(
            MapEventFilters(
                boundary_id=adm1["id"],
                event_type=EventCategory.FLOOD,
                processing_status=ProcessingStatus.COMPLETE,
                observed_after=observed_at - timedelta(minutes=1),
                observed_before=observed_at + timedelta(minutes=2),
                limit=1_000,
            )
        )
    )
    assert {feature["properties"]["id"] for feature in adm1_features} == {
        str(event_id) for event_id in matching_ids
    }
    assert len({feature["properties"]["id"] for feature in adm1_features}) == len(adm1_features)
    assert str(outside_id) not in {feature["properties"]["id"] for feature in adm1_features}
    assert str(null_id) not in {feature["properties"]["id"] for feature in adm1_features}

    adm2_features = asyncio.run(
        provider.geojson_features(MapEventFilters(boundary_id=adm2["id"], limit=1_000))
    )
    assert str(adm2_id) in {feature["properties"]["id"] for feature in adm2_features}
    lakshadweep_features = asyncio.run(
        provider.geojson_features(MapEventFilters(boundary_id=lakshadweep["id"], limit=1_000))
    )
    assert str(lakshadweep_id) in {
        feature["properties"]["id"] for feature in lakshadweep_features
    }

    with _boundary_test_client(session) as client:
        params = {
            "boundary_id": str(adm1["id"]),
            "event_type": "FLOOD",
            "processing_status": "COMPLETE",
            "date_from": (observed_at - timedelta(minutes=1)).isoformat(),
            "date_to": (observed_at + timedelta(minutes=2)).isoformat(),
            "page_size": 100,
            "limit": 1_000,
        }
        listed = client.get("/api/v1/events", params=params)
        mapped = client.get("/api/v1/events/map/events", params=params)
        assert listed.status_code == 200
        assert mapped.status_code == 200
        assert listed.json()["total"] == 2
        assert {item["id"] for item in listed.json()["items"]} == {
            feature["properties"]["id"] for feature in mapped.json()["features"]
        }
        unknown = client.get("/api/v1/events/map/events", params={"boundary_id": str(uuid4())})
        assert unknown.status_code == 422


def test_boundary_regional_summary_reconciles_real_boundary_results(session: Session) -> None:
    source_id = session.scalar(text("SELECT id FROM sources ORDER BY id LIMIT 1"))
    assert source_id is not None
    adm1 = _boundary_point(session, "ADM1")
    adm2 = _boundary_point(session, "ADM2")
    lakshadweep = session.execute(
        text(
            """SELECT id, ST_X(ST_PointOnSurface(geometry)) AS longitude,
                      ST_Y(ST_PointOnSurface(geometry)) AS latitude
               FROM administrative_boundaries
               WHERE administrative_level = 'ADM2' AND name ILIKE '%Lakshadweep%'"""
        )
    ).mappings().one()
    observed_at = datetime(2026, 9, 21, 12, tzinfo=UTC)
    state_event, district_event, unmatched_event, missing_event, lakshadweep_event = (
        uuid4() for _ in range(5)
    )
    for event_id, longitude, latitude in (
        (state_event, adm1["longitude"], adm1["latitude"]),
        (district_event, adm2["longitude"], adm2["latitude"]),
        (unmatched_event, 0.0, 0.0),
        (lakshadweep_event, lakshadweep["longitude"], lakshadweep["latitude"]),
    ):
        _insert_event(
            session,
            source_id,
            event_id,
            float(longitude),
            observed_at,
            EventCategory.FLOOD,
            latitude=float(latitude),
        )
    _insert_event(
        session,
        source_id,
        missing_event,
        None,
        observed_at,
        EventCategory.FLOOD,
        latitude=None,
    )
    session.flush()
    query = GeographicAggregationFilters(
        event_type=EventCategory.FLOOD,
        severity="HIGH",
        processing_status=ProcessingStatus.COMPLETE,
        admin_status=AdminStatus.UNREVIEWED,
        observed_after=observed_at - timedelta(minutes=1),
        observed_before=observed_at + timedelta(minutes=1),
    )
    provider = PostgisGeospatialProvider(session)
    adm1_result = asyncio.run(provider.boundary_regional_summary(query, "ADM1"))
    assert adm1_result["filtered_event_count"] == 5
    assert adm1_result["categories"]["UNMATCHED"] >= 1
    assert adm1_result["categories"]["NO_COORDINATES"] == 1
    assert sum(row["event_count"] for row in adm1_result["regions"]) + sum(
        adm1_result["categories"].values()
    ) == 5

    adm2_result = asyncio.run(provider.boundary_regional_summary(query, "ADM2"))
    assert any(row["administrative_name"] == "Lakshadweep" for row in adm2_result["regions"])
    assert sum(row["event_count"] for row in adm2_result["regions"]) + sum(
        adm2_result["categories"].values()
    ) == 5

    dataset_id = session.scalar(
        text("SELECT dataset_id FROM administrative_boundaries WHERE id = CAST(:id AS uuid)"),
        {"id": str(adm1["id"])},
    )
    session.execute(
        text(
            """INSERT INTO administrative_boundaries (
                    id, dataset_id, administrative_level, source_feature_id, name, geometry
                ) VALUES (
                    CAST(:id AS uuid), CAST(:dataset_id AS uuid), 'ADM1', :source_feature_id,
                    'Synthetic overlap edge fixture', ST_Multi(ST_Buffer(
                        ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326), 0.01
                    ))
                )"""
        ),
        {
            "id": str(uuid4()),
            "dataset_id": str(dataset_id),
            "source_feature_id": f"synthetic-{uuid4()}",
            "longitude": float(adm1["longitude"]),
            "latitude": float(adm1["latitude"]),
        },
    )
    ambiguous_result = asyncio.run(provider.boundary_regional_summary(query, "ADM1"))
    assert ambiguous_result["categories"]["AMBIGUOUS"] == 1
    assert sum(row["event_count"] for row in ambiguous_result["regions"]) + sum(
        ambiguous_result["categories"].values()
    ) == 5

    with _boundary_test_client(session) as client:
        default_response = client.get("/api/v1/geo/regions/summary")
        assert default_response.status_code == 200
        assert isinstance(default_response.json(), list)
        params = {
            "grouping_method": "BOUNDARY_DERIVED_LOCATION",
            "administrative_level": "ADM2",
            "event_type": "FLOOD",
            "severity": "HIGH",
            "processing_status": "COMPLETE",
            "admin_status": "UNREVIEWED",
            "date_from": (observed_at - timedelta(minutes=1)).isoformat(),
            "date_to": (observed_at + timedelta(minutes=1)).isoformat(),
        }
        response = client.get("/api/v1/geo/regions/summary", params=params)
        assert response.status_code == 200
        assert response.json()["administrative_level"] == "ADM2"
        assert response.json()["filtered_event_count"] == 5
        assert client.get(
            "/api/v1/geo/regions/summary", params={"grouping_method": "invalid"}
        ).status_code == 422
        assert client.get(
            "/api/v1/geo/regions/summary", params={"administrative_level": "ADM3"}
        ).status_code == 422


def test_display_boundaries_are_valid_and_do_not_change_authoritative_matches(session: Session) -> None:
    geometry_check = session.execute(
        text(
            """SELECT count(*) AS features, bool_and(ST_IsValid(display_geometry)) AS valid,
                      bool_and(NOT ST_IsEmpty(display_geometry)) AS non_empty,
                      sum(ST_NPoints(geometry)) > sum(ST_NPoints(display_geometry)) AS reduced
               FROM (
                   SELECT geometry, CASE WHEN ST_IsValid(ST_Multi(ST_Transform(
                       ST_SimplifyPreserveTopology(ST_Transform(geometry, 6933), 1000), 4326)))
                       THEN ST_Multi(ST_Transform(ST_SimplifyPreserveTopology(
                           ST_Transform(geometry, 6933), 1000), 4326)) ELSE geometry END AS display_geometry
                   FROM administrative_boundaries WHERE administrative_level = 'ADM1'
               ) boundaries"""
        )
    ).mappings().one()
    assert geometry_check == {"features": 36, "valid": True, "non_empty": True, "reduced": True}
    expected_ids = set(
        session.scalars(
            text("SELECT id::text FROM administrative_boundaries WHERE administrative_level = 'ADM1'")
        ).all()
    )
    with _boundary_test_client(session) as client:
        response = client.get("/api/v1/geo/boundaries?level=ADM1&limit=36&geometry_purpose=display")
    assert response.status_code == 200
    assert {feature["properties"]["boundary_uuid"] for feature in response.json()["features"]} == expected_ids

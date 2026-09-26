import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

POSTGIS_TEST_DATABASE_URL = os.getenv("POSTGIS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not POSTGIS_TEST_DATABASE_URL, reason="POSTGIS_TEST_DATABASE_URL is required for PostGIS integration tests"
)


@pytest.fixture
def engine():
    assert POSTGIS_TEST_DATABASE_URL
    database_engine = create_engine(POSTGIS_TEST_DATABASE_URL)
    yield database_engine
    database_engine.dispose()


def test_postgis_location_schema_and_existing_coordinate_order(engine) -> None:
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT PostGIS_Version()"))
        assert connection.scalar(
            text("SELECT count(*) FROM pg_indexes WHERE indexname = 'ix_weather_events_location_gist'")
        ) == 1
        row = connection.execute(
            text(
                """
                SELECT count(*) AS events, count(location) AS locations,
                       count(*) FILTER (WHERE ST_SRID(location::geometry) = 4326) AS correct_srid,
                       count(*) FILTER (WHERE ST_X(location::geometry) = longitude
                                         AND ST_Y(location::geometry) = latitude) AS correct_order
                FROM weather_events
                """
            )
        ).mappings().one()
    assert row == {"events": 39, "locations": 39, "correct_srid": 39, "correct_order": 39}


def test_coordinate_pair_constraint_rejects_partial_update(engine) -> None:
    with engine.connect() as connection:
        transaction = connection.begin()
        event_id = connection.scalar(text("SELECT id FROM weather_events LIMIT 1"))
        with pytest.raises(IntegrityError):
            connection.execute(
                text("UPDATE weather_events SET latitude = NULL WHERE id = :event_id"),
                {"event_id": event_id},
            )
        transaction.rollback()

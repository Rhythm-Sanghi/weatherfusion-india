"""Enable PostGIS and add a derived WeatherEvent geography location."""

from alembic import op

revision = "20260919_04"
down_revision = "20260919_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute(
        """
        ALTER TABLE weather_events
        ADD COLUMN location geography(Point, 4326)
        GENERATED ALWAYS AS (
            CASE
                WHEN latitude IS NULL AND longitude IS NULL THEN NULL
                ELSE ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography
            END
        ) STORED
        """
    )
    op.execute(
        """
        ALTER TABLE weather_events
        ADD CONSTRAINT ck_events_coordinate_pair
        CHECK ((latitude IS NULL) = (longitude IS NULL))
        """
    )
    op.execute(
        """
        CREATE INDEX ix_weather_events_location_gist
        ON weather_events USING GIST (location)
        WHERE location IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_weather_events_location_gist")
    op.execute("ALTER TABLE weather_events DROP CONSTRAINT IF EXISTS ck_events_coordinate_pair")
    op.execute("ALTER TABLE weather_events DROP COLUMN IF EXISTS location")

"""phase 2 event foundation

Revision ID: 20260918_01
Revises:
Create Date: 2026-09-18
"""

import sqlalchemy as sa
from alembic import op

revision = "20260918_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("reliability", sa.Float(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_sources_name", "sources", ["name"])
    op.create_index("ix_sources_source_type", "sources", ["source_type"])
    op.create_table(
        "raw_ingest_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=160), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("validation_status", sa.String(length=32), nullable=False),
        sa.Column("validation_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_raw_ingest_records_source_id", "raw_ingest_records", ["source_id"])
    op.create_table(
        "weather_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=160), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processing_status", sa.String(length=16), nullable=False),
        sa.Column("system_assessment", sa.String(length=16), nullable=False),
        sa.Column("admin_status", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)", name="ck_events_latitude"
        ),
        sa.CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="ck_events_longitude",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_weather_events_source_id", "weather_events", ["source_id"])
    op.create_index("ix_weather_events_event_type", "weather_events", ["event_type"])
    op.create_index("ix_weather_events_severity", "weather_events", ["severity"])
    op.create_index("ix_weather_events_state", "weather_events", ["state"])
    op.create_index("ix_weather_events_observed_at", "weather_events", ["observed_at"])
    op.create_index("ix_weather_events_processing_status", "weather_events", ["processing_status"])
    op.create_index("ix_weather_events_system_assessment", "weather_events", ["system_assessment"])
    op.create_index("ix_weather_events_admin_status", "weather_events", ["admin_status"])
    op.create_index(
        "ix_weather_events_filters", "weather_events", ["event_type", "state", "severity"]
    )
    op.create_index(
        "ix_weather_events_statuses",
        "weather_events",
        ["processing_status", "system_assessment", "admin_status"],
    )
    op.create_index(
        "uq_weather_events_source_external_id",
        "weather_events",
        ["source_id", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_table("weather_events")
    op.drop_table("raw_ingest_records")
    op.drop_table("sources")

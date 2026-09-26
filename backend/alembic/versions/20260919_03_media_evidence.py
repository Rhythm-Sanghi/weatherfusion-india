"""Add metadata-only media evidence records."""

import sqlalchemy as sa
from alembic import op

revision = "20260919_03"
down_revision = "20260919_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("media_type", sa.String(length=16), nullable=False),
        sa.Column("reference", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("caption", sa.String(length=500), nullable=True),
        sa.Column("source_name", sa.String(length=160), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["weather_events.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_evidence_event_id", "media_evidence", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_media_evidence_event_id", table_name="media_evidence")
    op.drop_table("media_evidence")

"""phase 4 review decisions and audit trail

Revision ID: 20260919_02
Revises: 20260918_01
"""

import sqlalchemy as sa
from alembic import op

revision = "20260919_02"
down_revision = "20260918_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("review_decisions", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("event_id", sa.Uuid(), nullable=False), sa.Column("action", sa.String(16), nullable=False), sa.Column("previous_admin_status", sa.String(16), nullable=False), sa.Column("new_admin_status", sa.String(16), nullable=False), sa.Column("reviewer_id", sa.String(100), nullable=False), sa.Column("reviewer_name", sa.String(160), nullable=False), sa.Column("reason", sa.String(500), nullable=False), sa.Column("notes", sa.Text(), nullable=True), sa.Column("event_version", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["event_id"], ["weather_events.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_review_decisions_event_id", "review_decisions", ["event_id"])
    op.create_table("audit_events", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("event_id", sa.Uuid(), nullable=False), sa.Column("event_type", sa.String(64), nullable=False), sa.Column("action", sa.String(64), nullable=False), sa.Column("actor_type", sa.String(32), nullable=False), sa.Column("actor_id", sa.String(100), nullable=False), sa.Column("actor_name", sa.String(160), nullable=False), sa.Column("previous_value", sa.String(64), nullable=True), sa.Column("new_value", sa.String(64), nullable=True), sa.Column("reason", sa.String(500), nullable=True), sa.Column("metadata", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["event_id"], ["weather_events.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_audit_events_event_id", "audit_events", ["event_id"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("review_decisions")

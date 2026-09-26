"""Add versioned administrative-boundary storage."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.types import UserDefinedType

revision = "20260919_05"
down_revision = "20260919_04"
branch_labels = None
depends_on = None


class MultiPolygon(UserDefinedType):
    def get_col_spec(self, **_: object) -> str:
        return "geometry(MultiPolygon,4326)"


def upgrade() -> None:
    op.create_table(
        "boundary_datasets",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("boundary_id", sa.String(80), nullable=False, unique=True), sa.Column("administrative_level", sa.String(16), nullable=False), sa.Column("source", sa.String(300), nullable=False), sa.Column("source_url", sa.Text(), nullable=False), sa.Column("license", sa.String(160), nullable=False), sa.Column("attribution", sa.Text(), nullable=False), sa.Column("version", sa.String(80), nullable=False), sa.Column("year_represented", sa.String(16), nullable=False), sa.Column("sha256", sa.String(64), nullable=False), sa.Column("feature_count", sa.Integer(), nullable=False), sa.Column("coverage_notes", sa.Text(), nullable=False), sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "administrative_boundaries",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("dataset_id", sa.Uuid(), sa.ForeignKey("boundary_datasets.id"), nullable=False), sa.Column("administrative_level", sa.String(16), nullable=False), sa.Column("source_feature_id", sa.String(100), nullable=False), sa.Column("name", sa.String(200), nullable=False), sa.Column("source_code", sa.String(100)), sa.Column("parent_boundary_id", sa.Uuid(), sa.ForeignKey("administrative_boundaries.id")), sa.Column("geometry", MultiPolygon(), nullable=False), sa.UniqueConstraint("dataset_id", "source_feature_id", name="uq_boundary_dataset_feature"),
    )
    op.execute("CREATE INDEX ix_administrative_boundaries_geometry_gist ON administrative_boundaries USING GIST (geometry)")


def downgrade() -> None:
    op.drop_table("administrative_boundaries")
    op.drop_table("boundary_datasets")

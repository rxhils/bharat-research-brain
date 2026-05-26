"""0016_pipeline_runs

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-05-26

Creates `pipeline_runs` — one row per nightly pipeline run (Chunk 4.6).
One row per run_date (unique), upserted on re-run.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "d2e3f4a5b6c7"
down_revision: str | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pipeline_runs",
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("agents_run", JSONB()),
        sa.Column("total_duration_seconds", sa.Integer()),
        sa.Column("error_message", sa.Text()),
        sa.UniqueConstraint("run_date", name="pipeline_runs_run_date_key"),
        sa.CheckConstraint(
            "status IN ('running','success','partial','failed','skipped')",
            name="pipeline_status_allowed",
        ),
    )
    op.create_index(
        "idx_pipeline_runs_started", "pipeline_runs", [sa.text("started_at DESC")]
    )

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0016_pipeline_runs', "
        "'Created pipeline_runs (nightly scheduler run log) for Phase 4.6', "
        "'phase-4-chunk-4.6'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0016_pipeline_runs'"
    )
    op.drop_index("idx_pipeline_runs_started", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")

"""0015_daily_reports

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
Create Date: 2026-05-26

Creates `daily_reports` — the daily research note (Chunk 4.4). One row per
report_date, upserted on re-run. `audit_passed` is set True later by the
Meta-Auditor (Chunk 4.5).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b0c1d2e3f4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_reports",
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("body_md", sa.Text(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("top_stocks", JSONB()),
        sa.Column("macro_summary", sa.Text()),
        sa.Column(
            "audit_passed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "generated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("report_date"),
    )
    op.create_index(
        "idx_daily_reports_date", "daily_reports", [sa.text("report_date DESC")]
    )

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0015_daily_reports', "
        "'Created daily_reports (daily research note) for Phase 4.4', "
        "'phase-4-chunk-4.4'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0015_daily_reports'"
    )
    op.drop_index("idx_daily_reports_date", table_name="daily_reports")
    op.drop_table("daily_reports")

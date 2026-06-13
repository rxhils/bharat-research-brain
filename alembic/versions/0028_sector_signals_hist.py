"""0028_sector_signals_hist

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-14

Chunk 5.2b Task 4 — historical sector-momentum signals for lookahead-free
backtesting. SEPARATE table from live `sector_signals`. One row per (sector,
computed_date): the sector's average 30-day return + a leading/neutral/lagging
classification (cross-sectional rank that day). Computed from prices_eod_adjusted
using only bars on-or-before that date. Sector momentum is same-day observable
(no reporting lag), so `computed_date` IS the availability date — no
publication_date column. DO NOTHING on conflict.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sector_signals_historical",
        sa.Column("sector", sa.String(length=32), nullable=False),
        sa.Column("computed_date", sa.Date(), nullable=False),
        sa.Column("avg_return_30d", sa.Numeric(8, 4)),
        sa.Column("stock_count", sa.Integer(), nullable=False),
        sa.Column("classification", sa.String(length=12), nullable=False),
        sa.Column(
            "source",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'backfill'"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("sector", "computed_date"),
        sa.CheckConstraint(
            "classification IN ('leading','neutral','lagging')",
            name="sector_hist_classification_allowed",
        ),
    )
    op.create_index(
        "idx_sector_hist_date",
        "sector_signals_historical",
        [sa.text("computed_date")],
    )
    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0028_sector_signals_hist', "
        "'Historical sector-momentum signals (lookahead-free) for Chunk 5.2b', "
        "'chunk-5.2b-task4'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0028_sector_signals_hist'"
    )
    op.drop_index("idx_sector_hist_date", table_name="sector_signals_historical")
    op.drop_table("sector_signals_historical")

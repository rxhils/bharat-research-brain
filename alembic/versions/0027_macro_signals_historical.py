"""0027_macro_signals_historical

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-14

Chunk 5.2b Task 3 — historical market-breadth signals for lookahead-free
backtesting. SEPARATE table from live `macro_signals`. One row per (indicator,
computed_date): advance_decline_ratio / pct_above_ema200 / new_high_low_ratio,
each computed from `prices_eod_adjusted` using ONLY bars on-or-before that date.
Breadth is same-day observable (no reporting lag), so `computed_date` IS the
availability date — no publication_date column. DO NOTHING on conflict.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "macro_signals_historical",
        sa.Column("indicator", sa.String(length=24), nullable=False),
        sa.Column("computed_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(14, 4)),
        sa.Column("signal", sa.String(length=12), nullable=False),
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
        sa.PrimaryKeyConstraint("indicator", "computed_date"),
    )
    op.create_index(
        "idx_macro_hist_date", "macro_signals_historical", [sa.text("computed_date")]
    )
    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0027_macro_signals_historical', "
        "'Historical market-breadth signals (lookahead-free) for Chunk 5.2b', "
        "'chunk-5.2b-task3'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version "
        "WHERE version_label = '0027_macro_signals_historical'"
    )
    op.drop_index("idx_macro_hist_date", table_name="macro_signals_historical")
    op.drop_table("macro_signals_historical")

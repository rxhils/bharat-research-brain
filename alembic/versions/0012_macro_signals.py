"""0012_macro_signals

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-05-26

Creates `macro_signals` — daily macro indicators (usd_inr, crude_brent,
nifty_50, india_10y) + a derived market-regime row (Chunk 4.1). Sources are
public + permitted (Frankfurter FX, Yahoo Finance). One row per
(indicator, computed_date), upserted on re-run.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8a9b0c1d2e3"
down_revision: str | None = "e7f8a9b0c1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "macro_signals",
        sa.Column("indicator", sa.String(length=24), nullable=False),
        sa.Column("computed_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(14, 4)),
        sa.Column("signal", sa.String(length=12), nullable=False),
        sa.Column("regime_weight", sa.Numeric(6, 4), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column(
            "fetched_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("indicator", "computed_date"),
        sa.CheckConstraint(
            "signal IN ('rising','falling','stable','unknown',"
            "'risk-on','risk-off','neutral')",
            name="macro_signal_allowed",
        ),
    )
    op.create_index(
        "idx_macro_signals_date",
        "macro_signals",
        [sa.text("computed_date DESC")],
    )

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0012_macro_signals', "
        "'Created macro_signals (macro indicators + market regime) for Phase 4.1', "
        "'phase-4-chunk-4.1'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0012_macro_signals'"
    )
    op.drop_index("idx_macro_signals_date", table_name="macro_signals")
    op.drop_table("macro_signals")

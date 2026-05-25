"""0006_prices_eod_adjusted

Revision ID: e1f2a3b4c5d7
Revises: d0e1f2a3b4c6
Create Date: 2026-05-25

Creates `prices_eod_adjusted` — back-adjusted EOD prices materialized by the
Adjusted Price Agent (Chunk 2.1). Same shape as prices_eod's OHLCV plus
adj_factor (cumulative split multiplier) and source='adjusted'. Composite PK
(trade_date, isin); the agent upserts so re-runs are idempotent.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d7"
down_revision: str | None = "d0e1f2a3b4c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "prices_eod_adjusted",
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("isin", sa.String(length=12), nullable=False),
        sa.Column("adj_open", sa.Numeric(18, 4)),
        sa.Column("adj_high", sa.Numeric(18, 4)),
        sa.Column("adj_low", sa.Numeric(18, 4)),
        sa.Column("adj_close", sa.Numeric(18, 4)),
        sa.Column("adj_volume", sa.BigInteger()),
        sa.Column("adj_factor", sa.Numeric(18, 8)),
        sa.Column(
            "source", sa.String(length=16), nullable=False, server_default="adjusted"
        ),
        sa.Column(
            "computed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["isin"], ["stocks.isin"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("trade_date", "isin"),
    )
    op.create_index(
        "idx_prices_adj_isin_date",
        "prices_eod_adjusted",
        ["isin", sa.text("trade_date DESC")],
    )

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0006_prices_eod_adjusted', "
        "'Created prices_eod_adjusted (back-adjusted OHLCV) for Phase 2.1', "
        "'phase-2-chunk-2.1'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0006_prices_eod_adjusted'"
    )
    op.drop_index("idx_prices_adj_isin_date", table_name="prices_eod_adjusted")
    op.drop_table("prices_eod_adjusted")

"""0009_fundamental_signals

Revision ID: c5d6e7f8a9b0
Revises: a3b4c5d6e7f9
Create Date: 2026-05-26

Creates `fundamental_signals` — weekly yfinance fundamentals snapshot per stock
(Chunk 3.4). One row per (isin, fetched_date), upserted on re-run. Drives the
`stocks.mcap_category` classification. `promoter_holding` is always NULL
(yfinance does not expose it).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5d6e7f8a9b0"
down_revision: str | None = "a3b4c5d6e7f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fundamental_signals",
        sa.Column("isin", sa.String(length=12), nullable=False),
        sa.Column("fetched_date", sa.Date(), nullable=False),
        sa.Column("pe_ratio", sa.Numeric(10, 2)),
        sa.Column("pb_ratio", sa.Numeric(10, 2)),
        sa.Column("roe", sa.Numeric(10, 4)),
        sa.Column("roce", sa.Numeric(10, 4)),
        sa.Column("debt_to_equity", sa.Numeric(10, 4)),
        sa.Column("revenue_growth", sa.Numeric(10, 4)),
        sa.Column("earnings_growth", sa.Numeric(10, 4)),
        sa.Column("profit_margin", sa.Numeric(10, 4)),
        sa.Column("market_cap", sa.BigInteger()),
        sa.Column("dividend_yield", sa.Numeric(8, 4)),
        sa.Column("promoter_holding", sa.Numeric(8, 4)),
        sa.Column("fifty_two_week_high", sa.Numeric(12, 2)),
        sa.Column("fifty_two_week_low", sa.Numeric(12, 2)),
        sa.Column("avg_volume_30d", sa.BigInteger()),
        sa.Column(
            "source",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'yfinance'"),
        ),
        sa.Column(
            "fetched_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("isin", "fetched_date"),
        sa.ForeignKeyConstraint(["isin"], ["stocks.isin"], ondelete="RESTRICT"),
    )
    op.create_index(
        "idx_fundamentals_isin_date",
        "fundamental_signals",
        ["isin", sa.text("fetched_date DESC")],
    )

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0009_fundamental_signals', "
        "'Created fundamental_signals (weekly yfinance fundamentals) for Phase 3.4', "
        "'phase-3-chunk-3.4'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0009_fundamental_signals'"
    )
    op.drop_index("idx_fundamentals_isin_date", table_name="fundamental_signals")
    op.drop_table("fundamental_signals")

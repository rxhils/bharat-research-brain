"""0026_fundamental_signals_historical

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-13

Chunk 5.2b Task 1 — historical quarterly fundamentals for lookahead-free
backtesting. SEPARATE table from the live `fundamental_signals` (do not pollute
live data). Each row carries a `publication_date` (= quarter_end + 45d reporting
lag); the backtest may only read a row when `trade_date >= publication_date`
(mle no-lookahead). One row per (isin, quarter_end_date), DO NOTHING on conflict.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fundamental_signals_historical",
        sa.Column("isin", sa.String(length=12), nullable=False),
        sa.Column("quarter_end_date", sa.Date(), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=False),
        sa.Column("pe_ratio", sa.Numeric(12, 4)),
        sa.Column("roe", sa.Numeric(12, 6)),
        sa.Column("debt_to_equity", sa.Numeric(12, 6)),
        sa.Column("fcf", sa.Numeric(20, 4)),
        sa.Column("revenue_growth_yoy", sa.Numeric(12, 6)),
        sa.Column(
            "source",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'yfinance'"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("isin", "quarter_end_date"),
        sa.ForeignKeyConstraint(["isin"], ["stocks.isin"], ondelete="RESTRICT"),
    )
    op.create_index(
        "idx_fund_hist_isin_pub",
        "fundamental_signals_historical",
        ["isin", "publication_date"],
    )
    op.create_index(
        "idx_fund_hist_pub",
        "fundamental_signals_historical",
        [sa.text("publication_date")],
    )
    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0026_fundamentals_historical', "
        "'Historical quarterly fundamentals (lookahead-free) for Chunk 5.2b', "
        "'chunk-5.2b-task1'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version "
        "WHERE version_label = '0026_fundamentals_historical'"
    )
    op.drop_index("idx_fund_hist_pub", table_name="fundamental_signals_historical")
    op.drop_index(
        "idx_fund_hist_isin_pub", table_name="fundamental_signals_historical"
    )
    op.drop_table("fundamental_signals_historical")

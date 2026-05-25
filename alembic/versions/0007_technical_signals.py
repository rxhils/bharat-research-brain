"""0007_technical_signals

Revision ID: f2a3b4c5d6e8
Revises: e1f2a3b4c5d7
Create Date: 2026-05-25

Creates `technical_signals` — nightly per-stock technical indicators computed
on adjusted prices by the Technical Agent (Chunk 3.1). PK (isin, computed_date);
the agent upserts as-of the latest adjusted trade date.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2a3b4c5d6e8"
down_revision: str | None = "e1f2a3b4c5d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "technical_signals",
        sa.Column("isin", sa.String(length=12), nullable=False),
        sa.Column("computed_date", sa.Date(), nullable=False),
        sa.Column("rsi_14", sa.Numeric(18, 4)),
        sa.Column("ema_20", sa.Numeric(18, 4)),
        sa.Column("ema_200", sa.Numeric(18, 4)),
        sa.Column("macd_line", sa.Numeric(18, 4)),
        sa.Column("macd_signal", sa.Numeric(18, 4)),
        sa.Column("macd_hist", sa.Numeric(18, 4)),
        sa.Column("atr_14", sa.Numeric(18, 4)),
        sa.Column("avg_delivery_pct_30d", sa.Numeric(8, 2)),
        sa.Column("price_vs_ema200", sa.String(length=8)),
        sa.Column("ema_cross", sa.String(length=8)),
        sa.Column(
            "source",
            sa.String(length=32),
            nullable=False,
            server_default="technical_agent",
        ),
        sa.Column(
            "computed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["isin"], ["stocks.isin"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("isin", "computed_date"),
        sa.CheckConstraint(
            "price_vs_ema200 IS NULL OR price_vs_ema200 IN ('above','below','at')",
            name="price_vs_ema200_allowed",
        ),
        sa.CheckConstraint(
            "ema_cross IS NULL OR ema_cross IN ('golden','death','none')",
            name="ema_cross_allowed",
        ),
    )
    op.create_index(
        "idx_technical_isin_date",
        "technical_signals",
        ["isin", sa.text("computed_date DESC")],
    )

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0007_technical_signals', "
        "'Created technical_signals (RSI/EMA/MACD/ATR/delivery) for Phase 3.1', "
        "'phase-3-chunk-3.1'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0007_technical_signals'"
    )
    op.drop_index("idx_technical_isin_date", table_name="technical_signals")
    op.drop_table("technical_signals")

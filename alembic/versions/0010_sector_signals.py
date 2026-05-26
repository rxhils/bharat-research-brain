"""0010_sector_signals

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-05-26

Creates `sector_signals` — daily sector-level momentum signals (Chunk 3.5),
computed purely by aggregating prices_eod_adjusted + technical_signals +
news_articles. One row per (sector, computed_date), upserted on re-run.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d6e7f8a9b0c1"
down_revision: str | None = "c5d6e7f8a9b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sector_signals",
        sa.Column("sector", sa.String(length=80), nullable=False),
        sa.Column("computed_date", sa.Date(), nullable=False),
        sa.Column("stock_count", sa.Integer(), nullable=False),
        sa.Column("avg_rsi_14", sa.Numeric(8, 4)),
        sa.Column("pct_above_ema200", sa.Numeric(8, 4)),
        sa.Column("momentum_7d", sa.Numeric(10, 4)),
        sa.Column("momentum_30d", sa.Numeric(10, 4)),
        sa.Column("avg_sentiment_score", sa.Numeric(8, 4)),
        sa.Column("bull_article_pct", sa.Numeric(8, 4)),
        sa.Column("signal", sa.String(length=8), nullable=False),
        sa.Column(
            "source",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'sector_agent'"),
        ),
        sa.Column(
            "computed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("sector", "computed_date"),
        sa.CheckConstraint(
            "signal IN ('leading','neutral','lagging')",
            name="sector_signal_allowed",
        ),
    )
    op.create_index(
        "idx_sector_signals_date",
        "sector_signals",
        [sa.text("computed_date DESC")],
    )

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0010_sector_signals', "
        "'Created sector_signals (sector momentum aggregation) for Phase 3.5', "
        "'phase-3-chunk-3.5'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0010_sector_signals'"
    )
    op.drop_index("idx_sector_signals_date", table_name="sector_signals")
    op.drop_table("sector_signals")

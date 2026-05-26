"""0014_stock_rankings

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
Create Date: 2026-05-26

Creates `stock_rankings` — the composite 0-100 morning score per stock
(Chunk 4.3), merging every signal table. One row per (isin, computed_date),
upserted on re-run. No external source.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "b0c1d2e3f4a5"
down_revision: str | None = "a9b0c1d2e3f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stock_rankings",
        sa.Column("isin", sa.String(length=12), nullable=False),
        sa.Column("computed_date", sa.Date(), nullable=False),
        sa.Column("composite_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("signal_label", sa.String(length=20), nullable=False),
        sa.Column("fundamental_score", sa.Numeric(6, 2)),
        sa.Column("technical_score", sa.Numeric(6, 2)),
        sa.Column("macro_score", sa.Numeric(6, 2)),
        sa.Column("sentiment_adj", sa.Numeric(6, 2)),
        sa.Column("risk_penalty", sa.Numeric(6, 2)),
        sa.Column("score_breakdown", JSONB()),
        sa.Column(
            "source",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'ranking_agent'"),
        ),
        sa.Column(
            "computed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("isin", "computed_date"),
        sa.ForeignKeyConstraint(["isin"], ["stocks.isin"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "signal_label IN ('bullish-watch','needs-confirmation','neutral',"
            "'cautious','avoid')",
            name="signal_label_allowed",
        ),
        sa.CheckConstraint(
            "composite_score >= 0 AND composite_score <= 100",
            name="composite_score_range",
        ),
    )
    op.create_index(
        "idx_stock_rankings_date_score",
        "stock_rankings",
        [sa.text("computed_date DESC"), sa.text("composite_score DESC")],
    )
    op.create_index(
        "idx_stock_rankings_isin_date",
        "stock_rankings",
        ["isin", sa.text("computed_date DESC")],
    )

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0014_stock_rankings', "
        "'Created stock_rankings (composite morning score) for Phase 4.3', "
        "'phase-4-chunk-4.3'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0014_stock_rankings'"
    )
    op.drop_index("idx_stock_rankings_isin_date", table_name="stock_rankings")
    op.drop_index("idx_stock_rankings_date_score", table_name="stock_rankings")
    op.drop_table("stock_rankings")

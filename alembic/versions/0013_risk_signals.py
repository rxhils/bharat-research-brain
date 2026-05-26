"""0013_risk_signals

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-05-26

Creates `risk_signals` — per-stock risk flags (Chunk 4.2), aggregated from
technical_signals + news_articles + macro_signals. One row per
(isin, computed_date), upserted on re-run. No external source.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9b0c1d2e3f4"
down_revision: str | None = "f8a9b0c1d2e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "risk_signals",
        sa.Column("isin", sa.String(length=12), nullable=False),
        sa.Column("computed_date", sa.Date(), nullable=False),
        sa.Column("atr_pct", sa.Numeric(8, 4)),
        sa.Column("volatility_flag", sa.String(length=8), nullable=False),
        sa.Column(
            "news_spike",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("days_to_results", sa.Integer()),
        sa.Column("risk_score", sa.Numeric(8, 2), nullable=False),
        sa.Column(
            "source",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'risk_agent'"),
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
            "volatility_flag IN ('low','medium','high')",
            name="volatility_flag_allowed",
        ),
        sa.CheckConstraint(
            "risk_score >= 0 AND risk_score <= 100", name="risk_score_range"
        ),
    )
    op.create_index(
        "idx_risk_signals_date", "risk_signals", [sa.text("computed_date DESC")]
    )
    op.create_index(
        "idx_risk_signals_isin_date",
        "risk_signals",
        ["isin", sa.text("computed_date DESC")],
    )

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0013_risk_signals', "
        "'Created risk_signals (per-stock risk flags + score) for Phase 4.2', "
        "'phase-4-chunk-4.2'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0013_risk_signals'"
    )
    op.drop_index("idx_risk_signals_isin_date", table_name="risk_signals")
    op.drop_index("idx_risk_signals_date", table_name="risk_signals")
    op.drop_table("risk_signals")

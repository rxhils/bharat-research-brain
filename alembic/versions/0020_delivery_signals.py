"""0020_delivery_signals

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-05-28

Creates `delivery_signals` — per-stock delivery-percentage snapshots (Build D).
File-ingested from an operator-downloaded Moneycontrol deliverables export (no
website scraping — CLAUDE.md §2 rule 5 allow-list). One row per (isin,
trade_date), upserted on re-ingest. High delivery % = lower intraday churn, a
proxy for genuine accumulation.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b6c7d8e9f0a1"
down_revision: str | None = "a5b6c7d8e9f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "delivery_signals",
        sa.Column("isin", sa.String(length=12), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("delivery_pct", sa.Numeric(8, 4), nullable=False),
        sa.Column("avg_5d_delivery_pct", sa.Numeric(8, 4)),
        sa.Column("traded_volume", sa.BigInteger()),
        sa.Column("delivery_volume", sa.BigInteger()),
        sa.Column(
            "source",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'moneycontrol'"),
        ),
        sa.Column(
            "fetched_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("isin", "trade_date"),
        sa.ForeignKeyConstraint(["isin"], ["stocks.isin"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "delivery_pct >= 0 AND delivery_pct <= 100", name="delivery_pct_range"
        ),
    )
    op.create_index(
        "idx_delivery_isin_date",
        "delivery_signals",
        ["isin", sa.text("trade_date DESC")],
    )

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0020_delivery_signals', "
        "'Created delivery_signals (delivery-pct snapshots) for Build D', "
        "'build-d-delivery'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0020_delivery_signals'"
    )
    op.drop_index("idx_delivery_isin_date", table_name="delivery_signals")
    op.drop_table("delivery_signals")

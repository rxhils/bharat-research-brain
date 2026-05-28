"""0022_stock_vcp_signals

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-05-28

Creates `stock_vcp_signals` — VCP / Minervini screener output per stock
(Chunk 4.10). One row per (isin, computed_date), upserted as-of the latest
adjusted trade date. `vcp_detected` is the hard gate; the component scores
(trend / quality / proximity / relative strength) and `vcp_score` composite are
nullable (stocks with too little history are recorded not-detected, NULL scores).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8e9f0a1b2c3"
down_revision: str | None = "c7d8e9f0a1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stock_vcp_signals",
        sa.Column("isin", sa.String(length=12), nullable=False),
        sa.Column("computed_date", sa.Date(), nullable=False),
        sa.Column("vcp_detected", sa.Boolean(), nullable=False),
        sa.Column("contraction_count", sa.Integer()),
        sa.Column("contraction_quality", sa.Numeric(6, 2)),
        sa.Column("volume_dryup", sa.Boolean()),
        sa.Column("trend_score", sa.Numeric(6, 2)),
        sa.Column("pivot_proximity", sa.Numeric(6, 2)),
        sa.Column("relative_strength", sa.Numeric(6, 2)),
        sa.Column("vcp_score", sa.Numeric(6, 2)),
        sa.Column(
            "source",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'vcp_agent'"),
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
            "contraction_count IS NULL OR contraction_count >= 0",
            name="vcp_contraction_count_nonneg",
        ),
    )
    op.create_index(
        "idx_vcp_isin_date",
        "stock_vcp_signals",
        ["isin", sa.text("computed_date DESC")],
    )
    op.create_index(
        "idx_vcp_detected",
        "stock_vcp_signals",
        [sa.text("computed_date DESC"), "vcp_detected"],
    )

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0022_stock_vcp_signals', "
        "'Created stock_vcp_signals (Minervini VCP screener) for Chunk 4.10', "
        "'chunk-4.10-vcp'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0022_stock_vcp_signals'"
    )
    op.drop_index("idx_vcp_detected", table_name="stock_vcp_signals")
    op.drop_index("idx_vcp_isin_date", table_name="stock_vcp_signals")
    op.drop_table("stock_vcp_signals")

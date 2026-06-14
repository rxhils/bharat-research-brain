"""0029_benchmark_index

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-15

Chunk 5.2c — published benchmark index series (e.g. Nifty 500 TRI) for FAIR,
no-lookahead backtest alpha. Real index values, not a home-built proxy. One row
per (index_name, trade_date). DO NOTHING on conflict at ingest.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "benchmark_index",
        sa.Column("index_name", sa.String(length=32), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("index_value", sa.Numeric(14, 4), nullable=False),
        sa.Column(
            "source",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'investing'"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("index_name", "trade_date"),
    )
    op.create_index(
        "idx_benchmark_index_name_date",
        "benchmark_index",
        ["index_name", sa.text("trade_date")],
    )
    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0029_benchmark_index', "
        "'Published benchmark index series (Nifty 500 TRI) for fair backtest alpha', "
        "'chunk-5.2c'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0029_benchmark_index'"
    )
    op.drop_index("idx_benchmark_index_name_date", table_name="benchmark_index")
    op.drop_table("benchmark_index")

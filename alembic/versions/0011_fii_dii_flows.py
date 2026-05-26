"""0011_fii_dii_flows

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-05-26

Creates `fii_dii_flows` — daily market-wide institutional flows (Chunk 3.6).
Source is NSDL/SEBI FPI figures ingested from a locally-downloaded file (NSE
website scraping barred by CLAUDE.md §2 rule 5 / §12). `fii_net_cr` = FPI net
equity (FII proxy); `dii_net_cr` nullable (not published by NSDL/SEBI). One row
per flow_date, upserted on re-run.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7f8a9b0c1d2"
down_revision: str | None = "d6e7f8a9b0c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fii_dii_flows",
        sa.Column("flow_date", sa.Date(), nullable=False),
        sa.Column("fii_net_cr", sa.Numeric(14, 2), nullable=False),
        sa.Column("dii_net_cr", sa.Numeric(14, 2)),
        sa.Column("fii_5d_sum", sa.Numeric(14, 2)),
        sa.Column("dii_5d_sum", sa.Numeric(14, 2)),
        sa.Column("fii_signal", sa.String(length=12), nullable=False),
        sa.Column(
            "source",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'nsdl_fpi'"),
        ),
        sa.Column(
            "fetched_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("flow_date"),
        sa.CheckConstraint(
            "fii_signal IN ('strong_buy','buy','neutral','sell','strong_sell')",
            name="fii_signal_allowed",
        ),
    )

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0011_fii_dii_flows', "
        "'Created fii_dii_flows (NSDL/SEBI FPI institutional flows) for Phase 3.6', "
        "'phase-3-chunk-3.6'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0011_fii_dii_flows'"
    )
    op.drop_table("fii_dii_flows")

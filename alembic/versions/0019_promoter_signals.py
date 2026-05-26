"""0019_promoter_signals

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-05-27

Creates `promoter_signals` — quarterly promoter holding + pledge per stock
(Chunk 4.9 improvement 5). File-ingested from operator-downloaded BSE
shareholding-pattern XBRL (no NSE scraping — CLAUDE.md §2 rule 5). One row per
(isin, report_date), upserted on re-ingest.

NOTE: the chunk spec named this migration 0018_promoter_signals, but 0018 was
taken by the macro VIX signal-CHECK extension (the spec wrongly assumed
improvement 1 needed no migration), so the promoter table lands at 0019.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a5b6c7d8e9f0"
down_revision: str | None = "f4a5b6c7d8e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "promoter_signals",
        sa.Column("isin", sa.String(length=12), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("promoter_holding_pct", sa.Numeric(8, 4)),
        sa.Column("promoter_pledged_pct", sa.Numeric(8, 4)),
        sa.Column("pledge_risk_flag", sa.Text(), nullable=False),
        sa.Column(
            "source",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'bse_xbrl_file'"),
        ),
        sa.Column(
            "fetched_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("isin", "report_date"),
        sa.ForeignKeyConstraint(["isin"], ["stocks.isin"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "pledge_risk_flag IN ('safe','moderate','high','critical')",
            name="pledge_risk_flag_allowed",
        ),
    )
    op.create_index(
        "idx_promoter_isin_date",
        "promoter_signals",
        ["isin", sa.text("report_date DESC")],
    )

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0019_promoter_signals', "
        "'Created promoter_signals (promoter holding + pledge risk) for Phase 4.9', "
        "'phase-4-chunk-4.9'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0019_promoter_signals'"
    )
    op.drop_index("idx_promoter_isin_date", table_name="promoter_signals")
    op.drop_table("promoter_signals")

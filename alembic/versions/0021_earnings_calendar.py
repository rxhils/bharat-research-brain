"""0021_earnings_calendar

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-05-28

Creates `earnings_calendar` — upcoming/announced quarterly result dates per stock
(Build E). File-ingested from an operator-downloaded Moneycontrol results-calendar
export (no website scraping — CLAUDE.md §2 rule 5 allow-list). One row per (isin,
result_date), upserted on re-ingest. Feeds the Risk Agent's `days_to_results`
(event-risk near results).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7d8e9f0a1b2"
down_revision: str | None = "b6c7d8e9f0a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "earnings_calendar",
        sa.Column("isin", sa.String(length=12), nullable=False),
        sa.Column("result_date", sa.Date(), nullable=False),
        sa.Column("quarter", sa.Text()),
        sa.Column(
            "status",
            sa.String(length=12),
            nullable=False,
            server_default=sa.text("'upcoming'"),
        ),
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
        sa.PrimaryKeyConstraint("isin", "result_date"),
        sa.ForeignKeyConstraint(["isin"], ["stocks.isin"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "status IN ('upcoming','announced','confirmed')",
            name="earnings_status_allowed",
        ),
    )
    op.create_index(
        "idx_earnings_result_date",
        "earnings_calendar",
        [sa.text("result_date")],
    )
    op.create_index(
        "idx_earnings_isin_date",
        "earnings_calendar",
        ["isin", sa.text("result_date")],
    )

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0021_earnings_calendar', "
        "'Created earnings_calendar (upcoming result dates) for Build E', "
        "'build-e-earnings'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0021_earnings_calendar'"
    )
    op.drop_index("idx_earnings_isin_date", table_name="earnings_calendar")
    op.drop_index("idx_earnings_result_date", table_name="earnings_calendar")
    op.drop_table("earnings_calendar")

"""0017_fundamentals_extension

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-05-26

Extends `fundamental_signals` (Chunk 4.8) with richer yfinance fields: free cash
flow, interest coverage, current ratio, dividend history, and last-4-quarter
profit/revenue trends with a derived direction. All columns are nullable and
additive — no new table, no PK change. The existing
ON CONFLICT (isin, fetched_date) DO UPDATE upsert is extended in the repository.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3f4a5b6c7d8"
down_revision: str | None = "d2e3f4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "fundamental_signals"

# (column name, type) — JSONB trend arrays hold the last 4 quarters, recent first.
_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("free_cash_flow", sa.BigInteger()),
    ("fcf_positive", sa.Boolean()),
    ("interest_coverage", sa.Numeric(10, 4)),
    ("current_ratio", sa.Numeric(10, 4)),
    ("dividend_consecutive_years", sa.Integer()),
    ("dividend_payout_ratio", sa.Numeric(8, 4)),
    ("quarterly_profit_trend", JSONB()),
    ("quarterly_revenue_trend", JSONB()),
    ("q_profit_direction", sa.Text()),
    ("q_revenue_direction", sa.Text()),
)


def upgrade() -> None:
    for name, type_ in _COLUMNS:
        op.add_column(_TABLE, sa.Column(name, type_, nullable=True))

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0017_fundamentals_extension', "
        "'Extended fundamental_signals with FCF, coverage, dividend, and "
        "quarterly-trend fields for Phase 4.8', "
        "'phase-4-chunk-4.8'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version "
        "WHERE version_label = '0017_fundamentals_extension'"
    )
    for name, _ in reversed(_COLUMNS):
        op.drop_column(_TABLE, name)

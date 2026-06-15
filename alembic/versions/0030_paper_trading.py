"""0030_paper_trading

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-15

Forward PAPER-TRADING ledger for the frozen F+ engine (commit 57e72d5). A real,
out-of-sample track record that starts at inception and only grows forward — NEVER
backfilled. Rs 10,00,000 starting capital. Four tables:
  paper_account       — singleton account state (cash/equity, inception date)
  paper_position      — every position opened, with its close on exit (immutable open
                        history; exit_* filled when closed)
  paper_equity_curve  — one row per trading day: blended equity + exposure + index
  paper_event_log     — append-only audit of every rebalance / breakdown / exposure move
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "paper_account",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("inception_date", sa.Date(), nullable=False),
        sa.Column(
            "starting_capital", sa.Numeric(18, 2), nullable=False,
            server_default=sa.text("1000000"),
        ),
        sa.Column("current_cash", sa.Numeric(18, 2), nullable=False),
        sa.Column("current_equity", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "last_updated", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "engine_version", sa.String(length=32), nullable=False,
            server_default=sa.text("'F+ 57e72d5'"),
        ),
        sa.Column(
            "score_source", sa.String(length=16), nullable=False,
            server_default=sa.text("'mechanical'"),
        ),
    )
    op.create_table(
        "paper_position",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("isin", sa.String(length=12), sa.ForeignKey("stocks.isin"), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("entry_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("shares", sa.Numeric(24, 8), nullable=False),
        sa.Column("exposure_at_entry", sa.Numeric(5, 2), nullable=False),
        sa.Column(
            "status", sa.String(length=8), nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column("exit_date", sa.Date(), nullable=True),
        sa.Column("exit_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("exit_reason", sa.String(length=16), nullable=True),
        sa.CheckConstraint("status IN ('open','closed')", name="paper_position_status"),
    )
    op.create_index(
        "idx_paper_position_open", "paper_position", ["status", "isin"],
        postgresql_where=sa.text("status = 'open'"),
    )
    op.create_table(
        "paper_equity_curve",
        sa.Column("trade_date", sa.Date(), primary_key=True),
        sa.Column("total_equity", sa.Numeric(18, 2), nullable=False),
        sa.Column("invested_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("cash_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("exposure_level", sa.Numeric(5, 2), nullable=False),
        sa.Column("nifty500_tri", sa.Numeric(14, 4), nullable=True),
        sa.Column("drawdown_pct", sa.Numeric(7, 2), nullable=False, server_default=sa.text("0")),
    )
    op.create_table(
        "paper_event_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("event_type", sa.String(length=24), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_paper_event_date", "paper_event_log", ["trade_date"])
    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0030_paper_trading', "
        "'Forward paper-trading ledger for the frozen F+ engine (Rs 10L)', "
        "'chunk-5.3-paper'"
        ")"
    )


def downgrade() -> None:
    op.execute("DELETE FROM schema_version WHERE version_label = '0030_paper_trading'")
    op.drop_index("idx_paper_event_date", table_name="paper_event_log")
    op.drop_table("paper_event_log")
    op.drop_table("paper_equity_curve")
    op.drop_index("idx_paper_position_open", table_name="paper_position")
    op.drop_table("paper_position")
    op.drop_table("paper_account")

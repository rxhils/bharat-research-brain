"""0032_multi_portfolio

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-20

ADDITIVE multi-portfolio infrastructure for the Maven paper books. Does NOT touch
the backtest engine, configs, or the gauntlet — only the live paper ledger.

- New `portfolios` registry: one row per portfolio slot, each with a status
  (live / coming_soon / archived), its engine commit, inception date and capital.
  Seeds all 9 slots; only "Quant" (= Enhanced F+, commit 6ced078) is live.
- Adds `portfolio_id` to the four paper tables so multiple books coexist, each
  tagged. paper_equity_curve's primary key becomes (portfolio_id, trade_date).
- Any pre-existing single-book paper rows are tagged to the archived "F+ classic"
  portfolio (prod-safe: the old F+ classic book is preserved, never relabelled as
  Enhanced F+, never merged into Quant).

Reversible. New portfolios go live later by flipping status coming_soon -> live.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PAPER_TABLES = ("paper_account", "paper_position", "paper_equity_curve", "paper_event_log")


def upgrade() -> None:
    op.create_table(
        "portfolios",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=32), nullable=False, unique=True),
        sa.Column("engine_commit", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False,
                  server_default=sa.text("'coming_soon'")),
        sa.Column("inception_date", sa.Date(), nullable=True),
        sa.Column("starting_capital", sa.Numeric(18, 2), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('live','coming_soon','archived')",
                           name="portfolios_status_chk"),
    )

    # Seed the 9 slots + the archived F+ classic record. Only Quant is live.
    op.execute(
        """
        INSERT INTO portfolios (name, engine_commit, status, inception_date,
                                starting_capital, description) VALUES
        ('Quant', '6ced078', 'live', DATE '2026-06-22', 1000000,
         'Enhanced F+ (vol-adjusted momentum + 6.5% cash yield), validated commit 6ced078 — flagship'),
        ('Momentum',    NULL, 'coming_soon', NULL, NULL, 'Awaiting its own validated engine'),
        ('Constrained', NULL, 'coming_soon', NULL, NULL, 'Awaiting its own validated engine'),
        ('Growth',      NULL, 'coming_soon', NULL, NULL, 'Awaiting its own validated engine'),
        ('Core',        NULL, 'coming_soon', NULL, NULL, 'Awaiting its own validated engine'),
        ('Defensive',   NULL, 'coming_soon', NULL, NULL, 'Awaiting its own validated engine'),
        ('Quality',     NULL, 'coming_soon', NULL, NULL, 'Awaiting its own validated engine'),
        ('Value',       NULL, 'coming_soon', NULL, NULL, 'Awaiting its own validated engine'),
        ('Income',      NULL, 'coming_soon', NULL, NULL, 'Awaiting its own validated engine'),
        ('F+ classic', '6417a74', 'archived', DATE '2026-04-15', 1000000,
         'F+ classic, 2026-04-15 onward — preserved fallback; archived ledger in paper_*_classic')
        """
    )

    # Tag the paper tables. Nullable first, backfill any existing single-book rows
    # to F+ classic, then enforce NOT NULL + FK.
    for tbl in _PAPER_TABLES:
        op.add_column(tbl, sa.Column("portfolio_id", sa.BigInteger(), nullable=True))
        op.execute(
            f"UPDATE {tbl} SET portfolio_id = "
            "(SELECT id FROM portfolios WHERE name = 'F+ classic') "
            "WHERE portfolio_id IS NULL"
        )
        op.alter_column(tbl, "portfolio_id", nullable=False)
        op.create_foreign_key(
            f"fk_{tbl}_portfolio", tbl, "portfolios", ["portfolio_id"], ["id"]
        )

    # paper_equity_curve: one curve per (portfolio, day).
    op.drop_constraint("pk_paper_equity_curve", "paper_equity_curve", type_="primary")
    op.create_primary_key(
        "pk_paper_equity_curve", "paper_equity_curve", ["portfolio_id", "trade_date"]
    )
    op.create_index("idx_paper_position_portfolio", "paper_position",
                    ["portfolio_id", "status"])

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ('0032_multi_portfolio', "
        "'Multi-portfolio registry + portfolio_id on paper tables (Maven slots)', "
        "'maven-multi-portfolio')"
    )


def downgrade() -> None:
    op.execute("DELETE FROM schema_version WHERE version_label = '0032_multi_portfolio'")
    op.drop_index("idx_paper_position_portfolio", table_name="paper_position")
    op.drop_constraint("pk_paper_equity_curve", "paper_equity_curve", type_="primary")
    op.create_primary_key("pk_paper_equity_curve", "paper_equity_curve", ["trade_date"])
    for tbl in _PAPER_TABLES:
        op.drop_constraint(f"fk_{tbl}_portfolio", tbl, type_="foreignkey")
        op.drop_column(tbl, "portfolio_id")
    op.drop_table("portfolios")

"""0025_outcome_log

Revision ID: a1b2c3d4e5f6
Revises: f0a1b2c3d4e5
Create Date: 2026-05-29

Phase 5, Chunk 5.1 — the Outcome Agent's storage.

`outcome_log`: one row per (isin, pick_date) tracking a ranking pick against its
actual 1d/5d forward returns (entry from prices_eod_adjusted on pick_date; exits
filled later from the same table — no future data is read as a feature, only as a
label). `xgboost_training`: the feature/target matrix appended once a 5d outcome
is known. Both upserted on their natural key.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f0a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outcome_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("isin", sa.String(length=12), nullable=False),
        sa.Column("pick_date", sa.Date(), nullable=False),
        sa.Column("signal_label", sa.Text(), nullable=False),
        sa.Column("composite_score", sa.Numeric(6, 2)),
        sa.Column("entry_price", sa.Numeric(12, 4)),
        sa.Column("exit_price_1d", sa.Numeric(12, 4)),
        sa.Column("exit_price_5d", sa.Numeric(12, 4)),
        sa.Column("return_1d_pct", sa.Numeric(8, 4)),
        sa.Column("return_5d_pct", sa.Numeric(8, 4)),
        sa.Column("direction_correct_1d", sa.Boolean()),
        sa.Column("direction_correct_5d", sa.Boolean()),
        sa.Column("technical_score", sa.Numeric(6, 2)),
        sa.Column("fundamental_score", sa.Numeric(6, 2)),
        sa.Column("macro_score", sa.Numeric(6, 2)),
        sa.Column("macro_regime", sa.Text()),
        sa.Column("india_vix", sa.Numeric(8, 4)),
        sa.Column("sector", sa.Text()),
        sa.Column("vcp_detected", sa.Boolean()),
        sa.Column("delivery_pct", sa.Numeric(8, 4)),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["isin"], ["stocks.isin"], ondelete="RESTRICT"),
        sa.UniqueConstraint("isin", "pick_date", name="uq_outcome_isin_pick_date"),
    )
    op.create_index(
        "idx_outcome_pick_date", "outcome_log", [sa.text("pick_date DESC")]
    )
    op.create_index("idx_outcome_isin_date", "outcome_log", ["isin", "pick_date"])

    op.create_table(
        "xgboost_training",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("isin", sa.Text(), nullable=False),
        sa.Column("pick_date", sa.Date(), nullable=False),
        sa.Column("f_technical_score", sa.Numeric(8, 4)),
        sa.Column("f_fundamental_score", sa.Numeric(8, 4)),
        sa.Column("f_macro_score", sa.Numeric(8, 4)),
        sa.Column("f_rsi_14", sa.Numeric(8, 4)),
        sa.Column("f_macd_hist", sa.Numeric(8, 4)),
        sa.Column("f_price_vs_ema200", sa.Numeric(8, 4)),
        sa.Column("f_pe_ratio", sa.Numeric(8, 4)),
        sa.Column("f_roe", sa.Numeric(8, 4)),
        sa.Column("f_revenue_growth", sa.Numeric(8, 4)),
        sa.Column("f_fii_signal_encoded", sa.Numeric(8, 4)),
        sa.Column("f_macro_regime_encoded", sa.Numeric(8, 4)),
        sa.Column("f_india_vix", sa.Numeric(8, 4)),
        sa.Column("f_vcp_score", sa.Numeric(8, 4)),
        sa.Column("f_delivery_pct", sa.Numeric(8, 4)),
        sa.Column("f_days_to_results", sa.Integer()),
        sa.Column("target_return_5d", sa.Numeric(8, 4)),
        sa.Column("target_direction_5d", sa.Boolean()),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "isin", "pick_date", name="uq_xgboost_isin_pick_date"
        ),
    )
    op.create_index(
        "idx_xgboost_pick_date", "xgboost_training", [sa.text("pick_date DESC")]
    )

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES "
        "('0025_outcome_log', "
        "'Created outcome_log + xgboost_training (Outcome Agent, Phase 5.1)', "
        "'phase-5-chunk-5.1')"
    )


def downgrade() -> None:
    op.execute("DELETE FROM schema_version WHERE version_label = '0025_outcome_log'")
    op.drop_index("idx_xgboost_pick_date", table_name="xgboost_training")
    op.drop_table("xgboost_training")
    op.drop_index("idx_outcome_isin_date", table_name="outcome_log")
    op.drop_index("idx_outcome_pick_date", table_name="outcome_log")
    op.drop_table("outcome_log")

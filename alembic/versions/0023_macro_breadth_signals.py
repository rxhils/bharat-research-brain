"""0023_macro_breadth_signals

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-05-29

Extends the `macro_signal_allowed` CHECK constraint on `macro_signals` to permit
the market-breadth signal vocabulary (Chunk 4.12): 'bullish'/'bearish' for
`pct_above_ema200` and 'strong'/'weak' for `new_high_low_ratio`. The breadth
rows reuse the existing `macro_signals` table (no new table); only the allowed
`signal` enum widens. `advance_decline_ratio` uses the existing
rising/falling/stable vocabulary and needs no change.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9f0a1b2c3d4"
down_revision: str | None = "d8e9f0a1b2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD = (
    "signal IN ('rising','falling','stable','unknown',"
    "'risk-on','risk-off','neutral','elevated','spike')"
)
_NEW = (
    "signal IN ('rising','falling','stable','unknown',"
    "'risk-on','risk-off','neutral','elevated','spike',"
    "'bullish','bearish','strong','weak')"
)


def upgrade() -> None:
    op.drop_constraint("macro_signal_allowed", "macro_signals", type_="check")
    op.create_check_constraint("macro_signal_allowed", "macro_signals", _NEW)

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0023_macro_breadth_signals', "
        "'Widened macro_signal_allowed CHECK for breadth signals (Chunk 4.12)', "
        "'chunk-4.12-breadth'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0023_macro_breadth_signals'"
    )
    op.drop_constraint("macro_signal_allowed", "macro_signals", type_="check")
    op.create_check_constraint("macro_signal_allowed", "macro_signals", _OLD)

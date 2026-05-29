"""0024_macro_scenario_event_signal

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
Create Date: 2026-05-29

Extends the `macro_signal_allowed` CHECK on `macro_signals` to permit the 8
scenario-event names (Chunk 4.13). The Macro Agent stores an `indicator=
'scenario_event'` row whose `signal` is the active event (e.g. 'VIX_SPIKE');
without this the existing CHECK rejects it. Reuses the existing table — only the
allowed `signal` enum widens (no new table, mirrors the 4.12 pattern in 0023).
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f0a1b2c3d4e5"
down_revision: str | None = "e9f0a1b2c3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD = (
    "signal IN ('rising','falling','stable','unknown',"
    "'risk-on','risk-off','neutral','elevated','spike',"
    "'bullish','bearish','strong','weak')"
)
_NEW = (
    "signal IN ('rising','falling','stable','unknown',"
    "'risk-on','risk-off','neutral','elevated','spike',"
    "'bullish','bearish','strong','weak',"
    "'RBI_RATE_CUT','RBI_RATE_HIKE','CRUDE_SPIKE','CRUDE_FALL',"
    "'INR_WEAKENS','INR_STRENGTHENS','US_FED_HIKE','VIX_SPIKE')"
)


def upgrade() -> None:
    op.drop_constraint("macro_signal_allowed", "macro_signals", type_="check")
    op.create_check_constraint("macro_signal_allowed", "macro_signals", _NEW)

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0024_macro_scenario_event_signal', "
        "'Widened macro_signal_allowed CHECK for 8 scenario-event names (Chunk 4.13)', "
        "'chunk-4.13-scenario-events'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version "
        "WHERE version_label = '0024_macro_scenario_event_signal'"
    )
    op.drop_constraint("macro_signal_allowed", "macro_signals", type_="check")
    op.create_check_constraint("macro_signal_allowed", "macro_signals", _OLD)

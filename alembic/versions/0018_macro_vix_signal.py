"""0018_macro_vix_signal

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-05-27

Extends the `macro_signals.signal` CHECK constraint (`macro_signal_allowed`) to
allow the India VIX fear levels 'elevated' and 'spike' (Chunk 4.9 improvement 1).
The chunk spec assumed no migration was needed, but the existing CHECK from
0012 only permitted rising/falling/stable/unknown/risk-on/risk-off/neutral, so a
'spike'/'elevated' india_vix row would be rejected. Reconciled via migration
(CLAUDE.md §15), not a vocabulary hack.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4a5b6c7d8e9"
down_revision: str | None = "e3f4a5b6c7d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT = "macro_signal_allowed"
_OLD = "'rising','falling','stable','unknown','risk-on','risk-off','neutral'"
_NEW = _OLD + ",'elevated','spike'"


def upgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "macro_signals", type_="check")
    op.create_check_constraint(
        _CONSTRAINT, "macro_signals", f"signal IN ({_NEW})"
    )
    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0018_macro_vix_signal', "
        "'Allowed india_vix signal values (elevated, spike) in macro_signals "
        "for Phase 4.9', "
        "'phase-4-chunk-4.9'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0018_macro_vix_signal'"
    )
    op.drop_constraint(_CONSTRAINT, "macro_signals", type_="check")
    op.create_check_constraint(
        _CONSTRAINT, "macro_signals", f"signal IN ({_OLD})"
    )

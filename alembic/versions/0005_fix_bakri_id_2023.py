"""0005_fix_bakri_id_2023

Revision ID: d0e1f2a3b4c6
Revises: c9d1e2f3a4b5
Create Date: 2026-05-25

Corrects a date error in 0004: Bakri Id 2023 was encoded as 2023-06-28 but
the actual NSE trading holiday was 2023-06-29. Surfaced by the Chunk 1.3
price-backfill dry-run, which attempted 2023-06-29 (mismarked open) and got
BHAVCOPY_MISSING while 2023-06-28 (a real trading day) was mismarked closed.

Swaps the two days for NSE + BSE:
  - 2023-06-28 -> open / regular (was closed / 'Bakri Id')
  - 2023-06-29 -> closed / 'Bakri Id' (was open / regular)

Net open-day count for 2023 is unchanged (still 245); only the two specific
dates move.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d0e1f2a3b4c6"
down_revision: str | None = "c9d1e2f3a4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE trading_calendar "
        "SET is_open = true, session_type = 'regular', holiday_name = NULL "
        "WHERE trade_date = '2023-06-28' AND exchange IN ('NSE','BSE')"
    )
    op.execute(
        "UPDATE trading_calendar "
        "SET is_open = false, session_type = 'closed', holiday_name = 'Bakri Id' "
        "WHERE trade_date = '2023-06-29' AND exchange IN ('NSE','BSE')"
    )
    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0005_fix_bakri_id_2023', "
        "'Corrected Bakri Id 2023 from Jun 28 to Jun 29 (NSE+BSE)', "
        "'phase-1-chunk-1.3'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0005_fix_bakri_id_2023'"
    )
    op.execute(
        "UPDATE trading_calendar "
        "SET is_open = false, session_type = 'closed', holiday_name = 'Bakri Id' "
        "WHERE trade_date = '2023-06-28' AND exchange IN ('NSE','BSE')"
    )
    op.execute(
        "UPDATE trading_calendar "
        "SET is_open = true, session_type = 'regular', holiday_name = NULL "
        "WHERE trade_date = '2023-06-29' AND exchange IN ('NSE','BSE')"
    )

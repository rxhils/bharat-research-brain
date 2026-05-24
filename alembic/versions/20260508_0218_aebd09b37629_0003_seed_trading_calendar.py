"""0003_seed_trading_calendar

Revision ID: aebd09b37629
Revises: b800cd761633
Create Date: 2026-05-08 02:18:57.318304

Seeds the NSE + BSE trading calendar for 2024-01-01 through 2027-12-31.
Reads from alembic/seeds/trading_calendar_2024_2027.csv (~2,922 rows).

Source URLs (operator must verify the dataset against the current
published lists before relying on it for trading-day decisions):
  - https://www.nseindia.com/resources/exchange-communication-holidays
  - https://www.bseindia.com/static/markets/marketinfo/listholi.aspx
  - NSE annual circulars for Diwali Muhurat session timing.

**Operator must verify these dates against current published exchange
holiday calendars before relying on this data for trading-day
decisions in agent code. Update via 0004_*.py if discrepancies found.**

NOTES:
- 2024-2025 dates are based on historical NSE circulars and are
  high-confidence.
- 2026-2027 dates are projected from Hindu lunisolar calendar
  calculations and should be reconciled when the official lists
  publish.
- Diwali Muhurat session 2026 falls on a Sunday (2026-11-08); NSE
  may shift or skip — verify and patch in 0004 if needed.
- BSE shares NSE holidays for purposes of this seed. ±1 day
  discrepancies (rare) reconciled in a follow-up migration.

Schema modeling note: muhurat days are encoded as a SINGLE row with
session_type='muhurat', is_open=true. The PK (trade_date, exchange)
prevents two rows per date, so the closed regular session and the
open muhurat session on the same date are folded into the muhurat
row.
"""
from __future__ import annotations

import csv
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aebd09b37629'
down_revision: str | None = 'b800cd761633'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_CALENDAR_TABLE = sa.Table(
    "trading_calendar",
    sa.MetaData(),
    sa.Column("trade_date", sa.Date()),
    sa.Column("exchange", sa.String(8)),
    sa.Column("is_open", sa.Boolean()),
    sa.Column("session_type", sa.String(16)),
    sa.Column("holiday_name", sa.String(80)),
)


def _load_csv() -> list[dict[str, object]]:
    csv_path = (
        Path(__file__).resolve().parent.parent
        / "seeds"
        / "trading_calendar_2024_2027.csv"
    )
    rows: list[dict[str, object]] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            holiday = r["holiday_name"].strip()
            rows.append({
                "trade_date": datetime.strptime(r["trade_date"], "%Y-%m-%d").date(),
                "exchange": r["exchange"].strip(),
                "is_open": r["is_open"].strip().lower() == "true",
                "session_type": r["session_type"].strip(),
                "holiday_name": holiday if holiday else None,
            })
    return rows


def upgrade() -> None:
    op.bulk_insert(_CALENDAR_TABLE, _load_csv())

    # Operational migration log — final op of every migration per spec §3.3.
    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0003_seed_trading_calendar', "
        "'Seeded ~2922 calendar rows for NSE+BSE 2024-2027 incl. Muhurat sessions', "
        "'phase-1-chunk-1.1'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0003_seed_trading_calendar'"
    )
    # Delete ONLY the rows this migration seeded — keyed by the exact
    # (trade_date, exchange) pairs from the CSV — so any operator-added
    # calendar rows inside the 2024-2027 range are preserved.
    conn = op.get_bind()
    stmt = sa.text(
        "DELETE FROM trading_calendar "
        "WHERE trade_date = :trade_date AND exchange = :exchange"
    )
    for row in _load_csv():
        conn.execute(
            stmt,
            {"trade_date": row["trade_date"], "exchange": row["exchange"]},
        )

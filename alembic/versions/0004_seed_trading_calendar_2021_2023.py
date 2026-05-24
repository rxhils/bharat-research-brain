"""0004_seed_calendar_2021_2023

Revision ID: c9d1e2f3a4b5
Revises: aebd09b37629
Create Date: 2026-05-25

Seeds the NSE + BSE trading calendar for 2021-01-01 through 2023-12-31,
extending backward from 0003 (which covers 2024-2027). Chunk 1.3's Price
Agent backfill is gated by this calendar; without 2021-2023 rows a 5-year
backfill silently clamped to ~2.4 years.

Generation rules (same shape as 0003's CSV):
  - Weekends (Sat/Sun)            -> is_open=false, session_type='closed',
                                     holiday_name='Weekend'
  - Published exchange holidays   -> is_open=false, session_type='closed',
                                     holiday_name=<name>
  - Diwali Muhurat sessions       -> is_open=true,  session_type='muhurat',
                                     holiday_name='Diwali Muhurat Trading'
  - Every other weekday           -> is_open=true,  session_type='regular'
  - BSE shares the NSE holiday set (0003 convention).

Inserts use ON CONFLICT (trade_date, exchange) DO NOTHING so any boundary
overlap with 0003 or operator-added rows is preserved.

**Operator must verify these 2021-2023 holiday dates against the NSE
published holiday circulars before relying on this data for critical
trading decisions. The dates below are from training data and may contain
errors (a wrong/missing holiday shifts that year's open-day count by 1).**
Source circulars:
  - https://www.nseindia.com/resources/exchange-communication-holidays
  - https://www.bseindia.com/static/markets/marketinfo/listholi.aspx
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import insert as pg_insert

# revision identifiers, used by Alembic.
revision: str = "c9d1e2f3a4b5"
down_revision: str | None = "aebd09b37629"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_EXCHANGES = ("NSE", "BSE")
_START = date(2021, 1, 1)
_END = date(2023, 12, 31)

# Diwali Muhurat sessions (operator-supplied dates).
_MUHURAT: frozenset[date] = frozenset(
    {date(2021, 11, 4), date(2022, 10, 24), date(2023, 11, 13)}
)

# Published NSE trading holidays falling in the seed range. BSE shares these.
_HOLIDAYS: dict[date, str] = {
    # ---- 2021 ----
    date(2021, 1, 26): "Republic Day",
    date(2021, 3, 11): "Mahashivratri",
    date(2021, 3, 29): "Holi",
    date(2021, 4, 2): "Good Friday",
    date(2021, 4, 14): "Dr. Ambedkar Jayanti",
    date(2021, 4, 21): "Ram Navami",
    date(2021, 5, 13): "Id-ul-Fitr (Ramzan Id)",
    date(2021, 7, 21): "Bakri Id",
    date(2021, 8, 19): "Muharram",
    date(2021, 9, 10): "Ganesh Chaturthi",
    date(2021, 10, 15): "Dussehra",
    date(2021, 11, 5): "Diwali Balipratipada",
    date(2021, 11, 19): "Gurunanak Jayanti",
    # ---- 2022 ----
    date(2022, 1, 26): "Republic Day",
    date(2022, 3, 1): "Mahashivratri",
    date(2022, 3, 18): "Holi",
    date(2022, 4, 14): "Mahavir Jayanti / Dr. Ambedkar Jayanti",
    date(2022, 4, 15): "Good Friday",
    date(2022, 5, 3): "Id-ul-Fitr (Ramzan Id)",
    date(2022, 8, 9): "Muharram",
    date(2022, 8, 15): "Independence Day",
    date(2022, 8, 31): "Ganesh Chaturthi",
    date(2022, 10, 5): "Dussehra",
    date(2022, 10, 26): "Diwali Balipratipada",
    date(2022, 11, 8): "Gurunanak Jayanti",
    # ---- 2023 ----
    date(2023, 1, 26): "Republic Day",
    date(2023, 3, 7): "Holi",
    date(2023, 3, 30): "Ram Navami",
    date(2023, 4, 4): "Mahavir Jayanti",
    date(2023, 4, 7): "Good Friday",
    date(2023, 4, 14): "Dr. Ambedkar Jayanti",
    date(2023, 5, 1): "Maharashtra Day",
    date(2023, 6, 28): "Bakri Id",
    date(2023, 8, 15): "Independence Day",
    date(2023, 9, 19): "Ganesh Chaturthi",
    date(2023, 10, 2): "Mahatma Gandhi Jayanti",
    date(2023, 10, 24): "Dussehra",
    date(2023, 11, 14): "Diwali Balipratipada",
    date(2023, 11, 27): "Gurunanak Jayanti",
    date(2023, 12, 25): "Christmas",
}


_CALENDAR_TABLE = sa.Table(
    "trading_calendar",
    sa.MetaData(),
    sa.Column("trade_date", sa.Date()),
    sa.Column("exchange", sa.String(8)),
    sa.Column("is_open", sa.Boolean()),
    sa.Column("session_type", sa.String(16)),
    sa.Column("holiday_name", sa.String(80)),
)


def _all_dates() -> list[date]:
    out: list[date] = []
    d = _START
    while d <= _END:
        out.append(d)
        d += timedelta(days=1)
    return out


def _build_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for d in _all_dates():
        if d in _MUHURAT:
            is_open, session_type, holiday = True, "muhurat", "Diwali Muhurat Trading"
        elif d in _HOLIDAYS:
            is_open, session_type, holiday = False, "closed", _HOLIDAYS[d]
        elif d.weekday() >= 5:  # 5=Sat, 6=Sun
            is_open, session_type, holiday = False, "closed", "Weekend"
        else:
            is_open, session_type, holiday = True, "regular", None
        for exch in _EXCHANGES:
            rows.append(
                {
                    "trade_date": d,
                    "exchange": exch,
                    "is_open": is_open,
                    "session_type": session_type,
                    "holiday_name": holiday,
                }
            )
    return rows


def upgrade() -> None:
    rows = _build_rows()
    stmt = (
        pg_insert(_CALENDAR_TABLE)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["trade_date", "exchange"])
    )
    op.get_bind().execute(stmt)

    op.execute(
        "INSERT INTO schema_version (version_label, description, chunk_reference) "
        "VALUES ("
        "'0004_seed_calendar_2021_2023', "
        "'Seeded NSE+BSE trading calendar 2021-2023', "
        "'phase-1-chunk-1.3'"
        ")"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM schema_version WHERE version_label = '0004_seed_calendar_2021_2023'"
    )
    # Delete only the exact (trade_date, exchange) pairs this migration seeds,
    # so operator-added rows in the range are preserved.
    conn = op.get_bind()
    stmt = sa.text(
        "DELETE FROM trading_calendar "
        "WHERE trade_date = :trade_date AND exchange = :exchange"
    )
    for d in _all_dates():
        for exch in _EXCHANGES:
            conn.execute(stmt, {"trade_date": d, "exchange": exch})

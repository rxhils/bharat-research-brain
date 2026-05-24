"""Shared helpers for the repository layer.

Repositories are thin data-access wrappers (no business logic). This module
holds the small primitives several of them share — currently just the IST
clock used to stamp SCD-2 `effective_from` / `effective_to` dates.

CLAUDE.md §8: IST for display/business dates, UTC for storage timestamps.
SCD effective dates are calendar dates in the exchange's timezone (IST).
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def today_ist() -> date:
    """Current calendar date in IST.

    Used as the default `effective_from` for newly opened SCD-2 rows and the
    `effective_to` for closed ones when the caller does not pass an explicit
    trade date.
    """
    return datetime.now(IST).date()

"""NSE archives data source — equity security master CSV.

URL: https://archives.nseindia.com/content/equities/EQUITY_L.csv
Per CLAUDE.md §2 rule 5, this is an exchange-published CSV (permitted).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from datetime import date, datetime
from io import StringIO

import structlog

from backend.data_sources._http import FetchMetadata, fetch_bytes

log = structlog.get_logger()


SECURITY_MASTER_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
ALLOWED_SERIES = frozenset({"EQ", "BE", "BZ"})

# NSE EQUITY_L.csv ships with a leading-space prefix on most non-first
# columns (" SERIES", " NAME OF COMPANY", etc.). Reader probes both forms.
_LISTED_DATE_FORMATS = ("%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d")


@dataclass(frozen=True)
class NSESecurity:
    nse_symbol: str
    company_name: str
    series: str
    listed_on: date | None
    paid_up_value: str
    market_lot: int | None
    isin: str
    face_value: str


def _col(row: dict[str, str], *names: str) -> str:
    """Return first non-empty value across multiple candidate column names."""
    for name in names:
        v = row.get(name)
        if v is not None:
            stripped = v.strip()
            if stripped:
                return stripped
    return ""


class NSEArchivesClient:
    """Async client for NSE archives — equity security master."""

    async def fetch_security_master(
        self,
        *,
        cache_ttl: int = 3600,
    ) -> tuple[list[NSESecurity], FetchMetadata]:
        body, meta = await fetch_bytes(SECURITY_MASTER_URL, cache_ttl=cache_ttl)
        rows = self._parse_csv(body)
        meta = replace(meta, row_count=len(rows))
        log.info(
            "nse_archives.fetched",
            count=len(rows),
            source_url=meta.source_url,
            http_status=meta.http_status,
            cache_hit=meta.cache_hit,
        )
        return rows, meta

    @staticmethod
    def _parse_csv(body: bytes) -> list[NSESecurity]:
        text = body.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(StringIO(text))
        out: list[NSESecurity] = []
        for row in reader:
            series = _col(row, "SERIES", " SERIES").upper()
            if series not in ALLOWED_SERIES:
                continue
            isin = _col(row, "ISIN NUMBER", " ISIN NUMBER")
            if not isin:
                continue
            symbol = _col(row, "SYMBOL")
            name = _col(row, "NAME OF COMPANY", " NAME OF COMPANY")

            listed_str = _col(row, "DATE OF LISTING", " DATE OF LISTING")
            listed_on: date | None = None
            for fmt in _LISTED_DATE_FORMATS:
                if not listed_str:
                    break
                try:
                    listed_on = datetime.strptime(listed_str, fmt).date()
                    break
                except ValueError:
                    continue

            market_lot_str = _col(row, "MARKET LOT", " MARKET LOT")
            try:
                market_lot = int(market_lot_str) if market_lot_str else None
            except ValueError:
                market_lot = None

            out.append(
                NSESecurity(
                    nse_symbol=symbol,
                    company_name=name,
                    series=series,
                    listed_on=listed_on,
                    paid_up_value=_col(row, "PAID UP VALUE", " PAID UP VALUE"),
                    market_lot=market_lot,
                    isin=isin,
                    face_value=_col(row, "FACE VALUE", " FACE VALUE"),
                )
            )
        return out

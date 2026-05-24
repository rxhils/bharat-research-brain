"""NSE end-of-day bhavcopy client.

Two URL formats (NSE changed the layout in 2021):

  NEW (2021-01-01 onwards, primary):
    https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{YYYYMMDD}_F_0000.csv.zip
  OLD (pre-2021, fallback):
    https://archives.nseindia.com/content/historical/EQUITIES/{YYYY}/{MON}/cm{DD}{MON}{YYYY}bhav.csv.zip

Each URL serves a ZIP containing one CSV. We download, extract in memory
(`zipfile.ZipFile` on `BytesIO`) — never to disk — and parse. Per CLAUDE.md
§2 rule 5 these are exchange-published files (permitted) and we cache for
1 hour. Soft-404 (HTTP 200 with an HTML body) is detected and treated as a
miss, same as the niftyindices client.
"""
from __future__ import annotations

import csv
import zipfile
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO

import structlog

from backend.data_sources._http import FetchMetadata, fetch_bytes
from backend.data_sources.niftyindices import _looks_like_html
from backend.errors import DataSourceError

log = structlog.get_logger()

NEW_BASE = "https://nsearchives.nseindia.com/content/cm/"
OLD_BASE = "https://archives.nseindia.com/content/historical/EQUITIES/"

ALLOWED_SERIES = frozenset({"EQ", "BE", "BZ"})
_DATE_FORMATS = ("%d-%b-%Y", "%Y-%m-%d", "%d-%m-%Y")
# Both bhavcopy formats report traded value in RUPEES (verified against live
# data 2026-05-25 — the build spec's "crores"/"lakhs" claims were wrong).
# crore = 1e7 rupees, so value_inr_cr = rupees / RUPEES_PER_CRORE.
RUPEES_PER_CRORE = Decimal(10_000_000)


# ---------------------------------------------------------------------------
# URL builders
# ---------------------------------------------------------------------------
def new_format_url(d: date) -> str:
    return f"{NEW_BASE}BhavCopy_NSE_CM_0_0_0_{d:%Y%m%d}_F_0000.csv.zip"


def old_format_url(d: date) -> str:
    mon = d.strftime("%b").upper()
    return f"{OLD_BASE}{d.year}/{mon}/cm{d:%d}{mon}{d.year}bhav.csv.zip"


# ---------------------------------------------------------------------------
# Row model + warnings
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BhavRow:
    isin: str
    trade_date: date | None
    series: str
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal | None
    volume: int | None
    value_inr_cr: Decimal | None
    trades_count: int | None
    delivery_qty: int | None
    delivery_pct: Decimal | None


@dataclass(frozen=True)
class FilterWarning:
    code: str
    isin: str
    trade_date: date | None
    message: str


# ---------------------------------------------------------------------------
# Value coercion
# ---------------------------------------------------------------------------
def _clean(v: str | None) -> str:
    return (v or "").strip()


def _dec(v: str | None) -> Decimal | None:
    s = _clean(v)
    if not s or s == "-":
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _int(v: str | None) -> int | None:
    s = _clean(v)
    if not s or s == "-":
        return None
    try:
        return int(Decimal(s))
    except InvalidOperation:
        return None


def _parse_date(s: str) -> date | None:
    s = _clean(s)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# CSV parsers
# ---------------------------------------------------------------------------
def parse_new_format(text: str) -> list[BhavRow]:
    """Parse the UDiFF CM bhavcopy (NSE's current format).

    Real columns: TtlTradgVol (volume), TtlTrfVal (traded value in RUPEES),
    TtlNbOfTxsExctd (trades). UDiFF carries no delivery columns, so
    delivery_qty / delivery_pct are always None here.
    """
    reader = csv.DictReader(StringIO(text))
    out: list[BhavRow] = []
    for row in reader:
        val = _dec(row.get("TtlTrfVal"))  # rupees
        out.append(
            BhavRow(
                isin=_clean(row.get("ISIN")),
                trade_date=_parse_date(row.get("TradDt", "")),
                series=_clean(row.get("SctySrs")).upper(),
                open=_dec(row.get("OpnPric")),
                high=_dec(row.get("HghPric")),
                low=_dec(row.get("LwPric")),
                close=_dec(row.get("ClsPric")),
                volume=_int(row.get("TtlTradgVol")),
                value_inr_cr=(val / RUPEES_PER_CRORE) if val is not None else None,
                trades_count=_int(row.get("TtlNbOfTxsExctd")),
                delivery_qty=None,
                delivery_pct=None,
            )
        )
    return out


def parse_old_format(text: str) -> list[BhavRow]:
    reader = csv.DictReader(StringIO(text))
    out: list[BhavRow] = []
    for row in reader:
        val = _dec(row.get("TOTTRDVAL"))  # rupees
        out.append(
            BhavRow(
                isin=_clean(row.get("ISIN")),
                trade_date=_parse_date(row.get("TIMESTAMP", "")),
                series=_clean(row.get("SERIES")).upper(),
                open=_dec(row.get("OPEN")),
                high=_dec(row.get("HIGH")),
                low=_dec(row.get("LOW")),
                close=_dec(row.get("CLOSE")),
                volume=_int(row.get("TOTTRDQTY")),
                value_inr_cr=(val / RUPEES_PER_CRORE) if val is not None else None,
                trades_count=_int(row.get("TOTALTRADES")),
                delivery_qty=_int(row.get("DELIV_QTY")),
                delivery_pct=_dec(row.get("DELIV_PER")),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Data quality filter
# ---------------------------------------------------------------------------
def _ohlc_violation(r: BhavRow) -> bool:
    o, h, low_, c = r.open, r.high, r.low, r.close
    if h is None or low_ is None:
        return False
    if h < low_:
        return True
    return any(px is not None and (px < low_ or px > h) for px in (o, c))


def filter_rows(
    rows: list[BhavRow], known_isins: set[str]
) -> tuple[list[BhavRow], list[FilterWarning]]:
    """Apply the data-quality rules. Returns (kept_rows, warnings).

    Skips (silently): series not in EQ/BE/BZ, ISIN outside our universe.
    Skips (with warning): close <= 0 (ZERO_OR_NEGATIVE_PRICE), OHLC sanity
    breach (OHLC_VIOLATION).
    """
    good: list[BhavRow] = []
    warnings: list[FilterWarning] = []
    for r in rows:
        if r.series not in ALLOWED_SERIES:
            continue
        if r.isin not in known_isins:
            continue
        if r.close is None or r.close <= 0:
            warnings.append(
                FilterWarning(
                    "ZERO_OR_NEGATIVE_PRICE", r.isin, r.trade_date, f"close={r.close}"
                )
            )
            continue
        if _ohlc_violation(r):
            warnings.append(
                FilterWarning(
                    "OHLC_VIOLATION",
                    r.isin,
                    r.trade_date,
                    f"o={r.open} h={r.high} l={r.low} c={r.close}",
                )
            )
            continue
        good.append(r)
    return good, warnings


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
class NSEBhavcopyClient:
    """Downloads + parses one trading day's bhavcopy (new format, old fallback)."""

    async def fetch_for_date(
        self, d: date, *, cache_ttl: int = 3600
    ) -> tuple[list[BhavRow], FetchMetadata]:
        """Fetch + parse the bhavcopy for `d`.

        Tries the new URL; on HTTP 404 or soft-404 falls back to the old URL.
        Any other error fails loud. Raises DataSourceError if both fail.
        """
        new_url = new_format_url(d)
        old_url = old_format_url(d)

        try:
            body, meta = await fetch_bytes(
                new_url,
                cache_ttl=cache_ttl,
                validate=lambda b: self._reject_html(b, new_url),
            )
            rows = parse_new_format(self._extract_csv(body))
        except DataSourceError as exc:
            if exc.status_code != 404 and exc.reason_code != "soft_404_html_body":
                raise
            log.warning(
                "bhavcopy.fallback_old",
                date=str(d),
                reason=exc.reason_code or f"status_{exc.status_code}",
            )
            body, meta = await fetch_bytes(
                old_url,
                cache_ttl=cache_ttl,
                validate=lambda b: self._reject_html(b, old_url),
            )
            rows = parse_old_format(self._extract_csv(body))

        meta = replace(meta, row_count=len(rows))
        log.info(
            "bhavcopy.fetched",
            date=str(d),
            count=len(rows),
            source_url=meta.source_url,
            cache_hit=meta.cache_hit,
        )
        return rows, meta

    @staticmethod
    def _reject_html(body: bytes, url: str) -> None:
        if _looks_like_html(body):
            preview = body[:120].decode("utf-8", errors="replace").replace("\n", " ")
            raise DataSourceError(
                f"soft-404 from {url} — HTTP 200 with HTML body: {preview!r}",
                status_code=200,
                reason_code="soft_404_html_body",
            )

    @staticmethod
    def _extract_csv(zip_bytes: bytes) -> str:
        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not names:
                raise DataSourceError("bhavcopy ZIP contained no CSV member")
            with zf.open(names[0]) as fh:
                return fh.read().decode("utf-8-sig", errors="replace")

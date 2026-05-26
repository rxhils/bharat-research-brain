"""FII/DII (FPI) flow Agent (Chunk 3.6) — market-wide institutional flows.

SOURCE NOTE (important): the chunk originally specced scraping
`nseindia.com/api/fiidiiTradeReact`, which violates CLAUDE.md §2 rule 5 / §12
(no NSE website scraping / bypassing browser blocks). Per operator decision the
data comes from a PERMITTED source — NSDL/SEBI FPI figures — ingested from a
locally-saved file the operator downloads. No automated NSE access, no header
spoofing.

Because NSDL/SEBI publish FPI (not the NSE FII/DII cash pair):
  * `fii_net_cr` holds FPI net equity investment (Cr) — the FII proxy.
  * `dii_net_cr` is NOT published by NSDL/SEBI → may be None (column nullable).

The math (`parse_flows_csv`, `compute_rolling`, `classify_fii_signal`) is pure
and source-independent. `fetch_flows` reads a local file and is resilient:
a missing/unreadable file logs a warning and returns [] (never crashes).
"""
from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import structlog

log = structlog.get_logger()

SOURCE = "nsdl_fpi"
_WINDOW = 5

# 5-day rolling-sum thresholds (crores).
_STRONG_BUY = Decimal("5000")
_BUY = Decimal("1000")
_SELL = Decimal("-1000")
_STRONG_SELL = Decimal("-5000")


@dataclass(frozen=True)
class RawFlow:
    flow_date: date
    fii_net_cr: Decimal
    dii_net_cr: Decimal | None


@dataclass(frozen=True)
class FlowRow:
    flow_date: date
    fii_net_cr: Decimal
    dii_net_cr: Decimal | None
    fii_5d_sum: Decimal | None
    dii_5d_sum: Decimal | None
    fii_signal: str
    source: str = SOURCE


def _parse_date(raw: str) -> date:
    """Accept ISO (YYYY-MM-DD) or NSDL-style DD-MMM-YYYY (e.g. 21-May-2026)."""
    s = raw.strip()
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date format: {raw!r}")


def _parse_decimal(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    s = raw.strip().replace(",", "")
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation as exc:
        raise ValueError(f"invalid decimal: {raw!r}") from exc


def parse_flows_csv(text: str) -> list[RawFlow]:
    """Parse a CSV (header flow_date,fii_net_cr,dii_net_cr) into RawFlow rows."""
    reader = csv.DictReader(io.StringIO(text))
    rows: list[RawFlow] = []
    for rec in reader:
        fii = _parse_decimal(rec.get("fii_net_cr"))
        if fii is None:
            continue  # FII net is required; skip blank/garbage lines
        rows.append(
            RawFlow(
                flow_date=_parse_date(rec["flow_date"]),
                fii_net_cr=fii,
                dii_net_cr=_parse_decimal(rec.get("dii_net_cr")),
            )
        )
    return rows


def classify_fii_signal(fii_5d_sum: Decimal | None) -> str:
    """Map a 5-day rolling FII sum (Cr) to a signal. None -> neutral."""
    if fii_5d_sum is None:
        return "neutral"
    if fii_5d_sum > _STRONG_BUY:
        return "strong_buy"
    if fii_5d_sum > _BUY:
        return "buy"
    if fii_5d_sum < _STRONG_SELL:
        return "strong_sell"
    if fii_5d_sum < _SELL:
        return "sell"
    return "neutral"


def _window_sum(values: Sequence[Decimal | None]) -> Decimal | None:
    """Sum a full window; None if it is short or contains any None."""
    if len(values) < _WINDOW or any(v is None for v in values):
        return None
    return sum((v for v in values if v is not None), Decimal(0))


def compute_rolling(raw: Sequence[RawFlow]) -> list[FlowRow]:
    """Sort ascending and attach 5-row rolling sums + FII signal (pure)."""
    ordered = sorted(raw, key=lambda r: r.flow_date)
    out: list[FlowRow] = []
    for i, r in enumerate(ordered):
        window = ordered[max(0, i - _WINDOW + 1) : i + 1]
        fii_sum = _window_sum([w.fii_net_cr for w in window])
        dii_sum = _window_sum([w.dii_net_cr for w in window])
        out.append(
            FlowRow(
                flow_date=r.flow_date,
                fii_net_cr=r.fii_net_cr,
                dii_net_cr=r.dii_net_cr,
                fii_5d_sum=fii_sum,
                dii_5d_sum=dii_sum,
                fii_signal=classify_fii_signal(fii_sum),
                source=SOURCE,
            )
        )
    return out


@dataclass
class FiiDiiResult:
    rows_parsed: int = 0
    rows_upserted: int = 0
    flows: list[FlowRow] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.flows is None:
            self.flows = []


class FiiDiiAgent:
    name = "fii_dii"

    async def fetch_flows(self, path: str | None) -> list[RawFlow]:
        """Read + parse the local NSDL/SEBI FPI file. Resilient: [] on any issue."""
        import asyncio

        if not path:
            log.warning("fii_dii.fetch.no_file", reason="no path provided")
            return []
        text = await asyncio.to_thread(self._read_file, path)
        if text is None:
            return []
        try:
            return parse_flows_csv(text)
        except ValueError as exc:
            log.warning("fii_dii.fetch.parse_failed", path=path, error=str(exc))
            return []

    @staticmethod
    def _read_file(path: str) -> str | None:
        """Blocking file read (run via to_thread). None if missing/unreadable."""
        from pathlib import Path

        p = Path(path)
        if not p.exists():
            log.warning("fii_dii.fetch.missing", path=path)
            return None
        try:
            return p.read_text(encoding="utf-8")
        except OSError as exc:
            log.warning("fii_dii.fetch.read_failed", path=path, error=str(exc))
            return None

    async def run(
        self, *, path: str | None = None, dry_run: bool = False
    ) -> FiiDiiResult:
        from backend.db.repositories import fii_dii as fii_repo
        from backend.db.session import SessionLocal

        raw = await self.fetch_flows(path)
        rows = compute_rolling(raw)
        result = FiiDiiResult(rows_parsed=len(rows), flows=rows)

        if not dry_run and rows:
            payload = [_row_to_dict(r) for r in rows]
            async with SessionLocal() as session:
                result.rows_upserted = await fii_repo.bulk_upsert(session, payload)
                await session.commit()

        log.info(
            "fii_dii.run.done",
            parsed=result.rows_parsed,
            upserted=result.rows_upserted,
            dry_run=dry_run,
        )
        return result


def _row_to_dict(row: FlowRow) -> dict[str, object]:
    return {
        "flow_date": row.flow_date,
        "fii_net_cr": row.fii_net_cr,
        "dii_net_cr": row.dii_net_cr,
        "fii_5d_sum": row.fii_5d_sum,
        "dii_5d_sum": row.dii_5d_sum,
        "fii_signal": row.fii_signal,
        "source": row.source,
    }

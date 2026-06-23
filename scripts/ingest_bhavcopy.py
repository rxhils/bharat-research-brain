#!/usr/bin/env python
"""Same-day EOD price ingest from the OFFICIAL NSE bhavcopy (UDiFF format).

Why: yfinance publishes NSE EOD with a ~1-day lag, so the 1 AM cron kept aborting
on stale data. The NSE daily bhavcopy is the exchange's own final price file,
published ~6-7 PM IST the SAME trading day — permitted (CLAUDE.md §2.5: downloadable
exchange bhavcopies; NOT website scraping). yfinance stays as a per-day fallback.

Corporate-action safety (the important part): the bhavcopy gives RAW close
(`ClsPric`) plus NSE's CA-ADJUSTED previous close (`PrvsClsgPric`). On a split/bonus
ex-date NSE pre-adjusts PrvsClsgPric, so the day's true return is `ClsPric /
PrvsClsgPric`. We chain-link our existing adjusted series forward with that return:

    adj_close_D = adj_close_(prev) * (ClsPric_D / PrvsClsgPric_D)

so a corporate action can NEVER create a fake gap that would wrongly trip the live
book's -15% breakdown stop. On a normal day PrvsClsgPric == the prior raw close, so
the return is the plain daily return and adj_close tracks raw exactly (matches the
yfinance-adjusted history at the seam, since raw==adjusted for post-CA/forward days).

Idempotent: ON CONFLICT (trade_date, isin) DO NOTHING (same as the yfinance loader).
Ingests day-by-day over OPEN NSE sessions so chain-linking is always vs the
immediately-prior trading day.

Usage:
    python -m scripts.ingest_bhavcopy                 # last stored -> latest session
    python -m scripts.ingest_bhavcopy --date 2026-06-22   # one specific day
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import io
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import SessionLocal

log = structlog.get_logger()
IST = timezone(timedelta(hours=5, minutes=30))
_Q4 = Decimal("0.0001")
_Q8 = Decimal("0.00000001")
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
_BHAV_URL = (
    "https://nsearchives.nseindia.com/content/cm/"
    "BhavCopy_NSE_CM_0_0_0_{ymd}_F_0000.csv.zip"
)
# Equity series we trade (cash-market equity). Excludes ETFs/SME/debt series.
_EQ_SERIES = {"EQ", "BE", "BZ"}

_SQL_UNIVERSE = text("SELECT isin FROM stocks WHERE delisted_on IS NULL")
_SQL_LAST = text("SELECT MAX(trade_date) FROM prices_eod_adjusted")
# Most recent stored adjusted close per ISIN strictly BEFORE :d (the chain-link base).
_SQL_PRIOR_ADJ = text(
    "SELECT DISTINCT ON (isin) isin, adj_close FROM prices_eod_adjusted "
    "WHERE trade_date < :d ORDER BY isin, trade_date DESC"
)
_SQL_OPEN_DAYS = text(
    "SELECT trade_date FROM trading_calendar "
    "WHERE is_open AND exchange='NSE' AND trade_date > :after AND trade_date <= :upto "
    "ORDER BY trade_date"
)
_SQL_NEW_RUN = text(
    "INSERT INTO data_ingestion_runs (agent_name, status) "
    "VALUES ('ingest_bhavcopy', 'running') RETURNING id"
)
_SQL_FINISH_RUN = text(
    "UPDATE data_ingestion_runs SET status='success', finished_at=now() WHERE id=:id"
)
_SQL_INS_RAW = text(
    "INSERT INTO prices_eod (trade_date, isin, open, high, low, close, volume, "
    "source, ingestion_run_id) VALUES (:d,:isin,:o,:h,:l,:c,:v,'nse_bhavcopy',:run) "
    "ON CONFLICT (trade_date, isin) DO NOTHING"
)
_SQL_INS_ADJ = text(
    "INSERT INTO prices_eod_adjusted (trade_date, isin, adj_open, adj_high, adj_low, "
    "adj_close, adj_volume, adj_factor, source) "
    "VALUES (:d,:isin,:ao,:ah,:al,:ac,:v,:f,'nse_bhavcopy') "
    "ON CONFLICT (trade_date, isin) DO NOTHING"
)


def _dec(x: str) -> Decimal | None:
    try:
        v = Decimal(x.strip())
        return v if v.is_finite() else None
    except Exception:  # noqa: BLE001
        return None


def chain_link_adj(close: Decimal, prev_close: Decimal | None,
                   prior_adj: Decimal | None) -> Decimal:
    """CA-safe adjusted close (pure). adj = prior_adj * close/prev_close when both a
    prior adjusted close and a positive bhavcopy prev-close exist; else fall back to
    the raw close (new listing / gap — best available, no fake jump to chain from)."""
    if prior_adj is not None and prev_close is not None and prev_close > 0:
        return (prior_adj * (close / prev_close)).quantize(_Q4)
    return close.quantize(_Q4)


def _download_bhavcopy(d: date) -> dict[str, dict] | None:
    """Download + parse one day's NSE bhavcopy. Returns {isin: {o,h,l,c,pc,v}} for
    equity series, or None if the file is unavailable (weekend/holiday/not-published)."""
    url = _BHAV_URL.format(ymd=d.strftime("%Y%m%d"))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed NSE host
            blob = resp.read()
    except Exception as exc:  # noqa: BLE001 - missing file / network; caller falls back
        log.warning("bhavcopy.download_failed", date=str(d), error=str(exc))
        return None
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            name = zf.namelist()[0]
            text_csv = zf.read(name).decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        log.warning("bhavcopy.unzip_failed", date=str(d), error=str(exc))
        return None
    out: dict[str, dict] = {}
    for row in csv.DictReader(io.StringIO(text_csv)):
        if row.get("SctySrs", "").strip() not in _EQ_SERIES:
            continue
        isin = (row.get("ISIN") or "").strip()
        c = _dec(row.get("ClsPric", ""))
        if not isin or c is None or c <= 0:
            continue
        out[isin] = {
            "o": _dec(row.get("OpnPric", "")) or c,
            "h": _dec(row.get("HghPric", "")) or c,
            "l": _dec(row.get("LwPric", "")) or c,
            "c": c,
            "pc": _dec(row.get("PrvsClsgPric", "")),
            "v": _dec(row.get("TtlTradgVol", "")),
        }
    return out or None


async def ingest_day(session: AsyncSession, d: date, universe: set[str],
                     run_id: int) -> int:
    """Ingest ONE trading day from the bhavcopy with chain-link adjustment. Returns
    rows written (0 if the bhavcopy is unavailable). No-lookahead: chain base is the
    latest stored adj_close strictly before d."""
    rows = _download_bhavcopy(d)
    if not rows:
        return 0
    prior = {i: Decimal(a) for i, a in (await session.execute(_SQL_PRIOR_ADJ, {"d": d})).all()}
    raw_b: list[dict] = []
    adj_b: list[dict] = []
    for isin, r in rows.items():
        if isin not in universe:
            continue
        c = r["c"]
        if r["h"] < r["l"]:  # prices_eod CHECK high>=low
            continue
        ac = chain_link_adj(c, r["pc"], prior.get(isin))
        f = (ac / c).quantize(_Q8) if c > 0 else Decimal("1")
        v = int(r["v"]) if r["v"] is not None and r["v"] >= 0 else None
        raw_b.append({"d": d, "isin": isin, "o": r["o"], "h": r["h"], "l": r["l"],
                      "c": c, "v": v, "run": run_id})
        adj_b.append({"d": d, "isin": isin, "ao": (r["o"] * f).quantize(_Q4),
                      "ah": (r["h"] * f).quantize(_Q4), "al": (r["l"] * f).quantize(_Q4),
                      "ac": ac, "v": v, "f": f})
    if raw_b:
        await session.execute(_SQL_INS_RAW, raw_b)
        await session.execute(_SQL_INS_ADJ, adj_b)
        await session.commit()
    return len(raw_b)


async def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Same-day NSE bhavcopy EOD ingest.")
    p.add_argument("--date", default=None, help="ingest one YYYY-MM-DD only")
    args = p.parse_args(argv)

    async with SessionLocal() as s:
        universe = {i for (i,) in (await s.execute(_SQL_UNIVERSE)).all()}
        run_id = (await s.execute(_SQL_NEW_RUN)).scalar_one()
        await s.commit()
        if args.date:
            days = [date.fromisoformat(args.date)]
        else:
            last = (await s.execute(_SQL_LAST)).scalar_one()
            upto = datetime.now(IST).date()
            days = [r[0] for r in (await s.execute(
                _SQL_OPEN_DAYS, {"after": last, "upto": upto})).all()]
        log.info("bhavcopy.start", days=len(days), universe=len(universe), run_id=run_id)
        total = 0
        for d in days:
            n = await ingest_day(s, d, universe, run_id)
            total += n
            print(f"  {d}: {n} rows", flush=True)
            if n == 0:
                log.warning("bhavcopy.day_empty", date=str(d))
        await s.execute(_SQL_FINISH_RUN, {"id": run_id})
        await s.commit()
        new_last = (await s.execute(_SQL_LAST)).scalar_one()
    print(f"\nDONE. {total} bhavcopy rows over {len(days)} day(s). Latest now {new_last}.")
    log.info("bhavcopy.done", rows=total, latest=str(new_last))


if __name__ == "__main__":
    asyncio.run(main())

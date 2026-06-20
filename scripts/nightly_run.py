#!/usr/bin/env python
"""Nightly orchestration for the Maven multi-portfolio paper books (the '24/7' engine).

Runs AFTER market close + EOD price ingest (cron ~19:30 IST). Idempotent and logged.

Loops over every LIVE portfolio (currently just "Quant" = Enhanced F+ 6ced078) and,
per book, does exactly what is due:
  - book not yet started AND as_of >= inception  -> FIRST ALLOCATION (first real picks)
  - already started                              -> DAILY mark + cut-on-breakdown,
      + WEEKLY (every 5 trading days) exposure rescale,
      + QUARTERLY (every 63 trading days) full Enhanced-F+ re-pick
Books with status != 'live' (coming_soon / archived) are skipped — they have no engine.

No-lookahead: as_of = the latest trading date with EOD prices; every decision reads
only data <= as_of. Idempotent: first_allocation is guarded by 'has the book started',
daily upserts ON CONFLICT, and the run is gated to as_of >= inception.

Usage:  python -m scripts.nightly_run        (cron: daily ~19:30 IST)
"""
from __future__ import annotations

import asyncio
import traceback
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import text

from backend.agents.run_log import heartbeat
from backend.config import settings
from backend.db.session import SessionLocal
from backend.paper import engine as E

log = structlog.get_logger()
IST = timezone(timedelta(hours=5, minutes=30))
RUN_AGENT = "NightlyRun"

_LATEST = text("SELECT MAX(trade_date) FROM prices_eod_adjusted")
_TD_SINCE = text(
    "SELECT COUNT(DISTINCT trade_date) FROM prices_eod_adjusted "
    "WHERE trade_date >= :inception AND trade_date <= :as_of"
)


async def _notify(msg: str) -> None:
    """Best-effort Telegram ping. No-op if creds are unset; never raises."""
    token, chat = settings.telegram_bot_token, settings.telegram_chat_id
    if not token or not chat:
        log.info("nightly.telegram.skipped", reason="no TELEGRAM_BOT_TOKEN/CHAT_ID")
        return
    try:
        import httpx

        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat, "text": msg, "disable_web_page_preview": True},
            )
    except Exception as exc:  # noqa: BLE001 - notification must not break the run
        log.warning("nightly.telegram.failed", error=str(exc))


async def _run_one(s, port: dict, as_of) -> str:  # noqa: ANN001
    """Advance ONE live portfolio by one trading day. Returns a status line."""
    pid, name, inc = port["id"], port["name"], port["inception_date"]
    if inc is None:
        return f"{name}: live but no inception_date set — skipped"
    acct = await E.get_account(s, pid)
    if acct is None:
        return f"{name}: no book yet (run create_book) — skipped"
    if as_of < inc:
        return f"{name}: as_of {as_of} < inception {inc} — waiting for Monday's run"

    if not await E.has_started(s, pid):
        res = await E.first_allocation(s, pid, as_of)
        return (f"{name}: FIRST ALLOCATION on {as_of} — {res['n']} names, "
                f"exposure {res['exposure']}, cash Rs {float(res['cash']):,.0f}")

    td = (await s.execute(_TD_SINCE, {"inception": inc, "as_of": as_of})).scalar_one()
    daily = await E.daily_mark(s, pid, as_of)
    extra = ""
    if td % E.EXPOSURE_CHECK_DAYS == 0:
        wk = await E.weekly_exposure(s, pid, as_of)
        extra += f", exposure {wk['exposure']} (changed={wk['changed']})"
    if td % E.REBALANCE_DAYS == 0:
        q = await E.quarterly_rebalance(s, pid, as_of)
        extra += f", QUARTERLY re-pick {q['names']} names @ {q['exposure']}"
    return (f"{name}: daily {as_of} (td#{td}) equity Rs {float(daily['equity']):,.0f}, "
            f"cash Rs {float(daily['cash']):,.0f}, cuts {daily['breakdown_cuts']}{extra}")


async def main() -> None:
    run_id = "nightly-" + datetime.now(IST).strftime("%Y%m%d-%H%M%S")
    started = datetime.now(IST)
    async with SessionLocal() as s:
        await heartbeat(s, run_id, RUN_AGENT, "running", started_at=started)
        try:
            ports = await E.live_portfolios(s)
            if not ports:
                msg = "No live portfolios — nothing to do."
                print(msg)
                await heartbeat(s, run_id, RUN_AGENT, "waiting", headline=msg,
                                started_at=started, finished_at=datetime.now(IST))
                return
            as_of = (await s.execute(_LATEST)).scalar_one()
            log.info("nightly.start", as_of=str(as_of), live=len(ports))
            lines = []
            for port in ports:
                line = await _run_one(s, port, as_of)
                print(line)
                lines.append(line)
            log.info("nightly.done", as_of=str(as_of))
            ok = f"✅ Nightly {as_of} | " + " | ".join(lines)
            await heartbeat(s, run_id, RUN_AGENT, "done", headline=ok[:480],
                            started_at=started, finished_at=datetime.now(IST),
                            duration_ms=int((datetime.now(IST) - started).total_seconds() * 1000))
            await _notify(ok[:1000])
        except Exception as exc:  # noqa: BLE001 - surface failure loudly, then re-raise
            err = f"❌ Nightly run FAILED: {type(exc).__name__}: {exc}"
            log.error("nightly.failed", error=str(exc), traceback=traceback.format_exc())
            print(err)
            await heartbeat(s, run_id, RUN_AGENT, "error", headline=err[:480],
                            started_at=started, finished_at=datetime.now(IST))
            await _notify(err)
            raise


if __name__ == "__main__":
    asyncio.run(main())

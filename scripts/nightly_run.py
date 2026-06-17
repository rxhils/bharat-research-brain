#!/usr/bin/env python
"""Nightly orchestration for the forward F+ paper portfolio (the '24/7' engine).

Runs AFTER market close + EOD price ingest. Idempotent and logged — safe to re-run.

Steps:
  1. (Agentic pipeline) — DEFERRED: live News/FII/Fundamental agents need API keys
     (NEWSAPI_KEY/FMP_KEY/FYERS_ACCESS_TOKEN are empty). Until those exist, the F+
     score is the MECHANICAL composite (the validated signal), computed inside the
     paper engine. When keys are added, swap the score source to stock_rankings here.
  2. Paper engine, as due by trading-day count since inception:
       - DAILY  : mark-to-market + cut-on-breakdown (every run)
       - WEEKLY : every 5 trading days — regime -> exposure rescale
       - QUARTERLY: every 63 trading days — full F+ name rebalance
  3. The equity curve + drawdown are updated by the daily step.
  4. Observability: writes an agent_run_log heartbeat (running/done/error) and, if
     TELEGRAM_BOT_TOKEN/CHAT_ID are set, sends a success/failure ping with the date
     + F+ status. Both are best-effort — they never alter or block the F+ decisions.

No-lookahead: as_of = the latest trading date that has EOD prices; every decision
reads only data <= as_of. Does nothing (cleanly) until inception has been committed.
Idempotent: daily_mark/weekly/quarterly upsert ON CONFLICT, and the run is gated to
as_of > inception, so a re-run on the same day is a no-op on the ledger.

Usage:  python -m scripts.nightly_run        (cron: daily ~19:00 IST)
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
_HOLDINGS = text("SELECT COUNT(*) FROM paper_position WHERE status = 'open'")


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


async def main() -> None:
    run_id = "nightly-" + datetime.now(IST).strftime("%Y%m%d-%H%M%S")
    started = datetime.now(IST)
    async with SessionLocal() as s:
        await heartbeat(s, run_id, RUN_AGENT, "running", started_at=started)
        try:
            acct = await E.get_account(s)
            if acct is None:
                msg = ("No paper_account yet — inception not committed. Nothing to do. "
                       "(Run scripts.paper_inception --commit on the cloud to go live.)")
                print(msg)
                await heartbeat(s, run_id, RUN_AGENT, "waiting", headline=msg,
                                started_at=started, finished_at=datetime.now(IST))
                return
            as_of = (await s.execute(_LATEST)).scalar_one()
            if as_of <= acct["inception_date"]:
                msg = (f"Latest price date {as_of} <= inception {acct['inception_date']}; "
                       "waiting for the next EOD. Nothing to do.")
                print(msg)
                await heartbeat(s, run_id, RUN_AGENT, "waiting", headline=msg,
                                started_at=started, finished_at=datetime.now(IST))
                return
            td = (await s.execute(
                _TD_SINCE, {"inception": acct["inception_date"], "as_of": as_of})).scalar_one()

            log.info("nightly.start", as_of=str(as_of), trading_days_since_inception=td)
            daily = await E.daily_mark(s, as_of)
            print(f"DAILY  {as_of}: equity Rs {float(daily['equity']):,.0f}, "
                  f"cash Rs {float(daily['cash']):,.0f}, breakdown_cuts {daily['breakdown_cuts']}")

            exposure = None
            if td % E.EXPOSURE_CHECK_DAYS == 0:
                wk = await E.weekly_exposure(s, as_of)
                exposure = wk["exposure"]
                print(f"WEEKLY {as_of}: regime exposure {wk['exposure']} "
                      f"(changed={wk['changed']})")
            if td % E.REBALANCE_DAYS == 0:
                q = await E.quarterly_rebalance(s, as_of)
                exposure = q["exposure"]
                print(f"QUARTERLY {as_of}: re-picked {q['names']} names at exposure "
                      f"{q['exposure']}")
            log.info("nightly.done", as_of=str(as_of))
            print(f"Nightly run complete for {as_of} (trading day #{td} since inception).")

            holds = (await s.execute(_HOLDINGS)).scalar_one()
            exp_txt = f"{exposure}" if exposure is not None else "unchanged"
            ok = (f"✅ Run complete, latest {as_of}, F+ holds {holds}, "
                  f"exposure {exp_txt}, equity Rs {float(daily['equity']):,.0f}, "
                  f"cash Rs {float(daily['cash']):,.0f}, breakdown_cuts "
                  f"{daily['breakdown_cuts']} (td #{td})")
            await heartbeat(s, run_id, RUN_AGENT, "done", headline=ok, started_at=started,
                            finished_at=datetime.now(IST),
                            duration_ms=int((datetime.now(IST) - started).total_seconds() * 1000))
            await _notify(ok)
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

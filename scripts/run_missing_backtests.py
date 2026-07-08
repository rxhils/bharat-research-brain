"""Run & PERSIST the backtests the site publishes but the repo never saved.

Audit 2026-07-08 found that the Concentrated (+152.66% / 12.63%) and Defensive
(+84.61% / 17.63%) headline cards on trymaven.in have NO stored provenance: no
artifact, no test, no vault lesson computes them (the engine only ever printed to
stdout). This script closes that gap: it runs the exact engines the live paper
books use, over the exact site window (2021-06-01 -> 2026-05-26), and SAVES a JSON
artifact so every published number becomes reproducible.

Engines (identical to backend/paper/engine.py _ENGINE_BY_NAME):
  * Quant / Enhanced F+  = enhanced_fplus()            (control; should reproduce +129.97%)
  * Concentrated         = Enhanced F+ with top_n=10   (voladj momentum + 6.5% cash, brakes on)
  * Defensive            = defensive()                 (lowvol + defensive_exposure + 6.5% cash)

Run (from repo root, DB reachable — e.g. inside docker compose or with a tunnel):

    POSTGRES_URL=postgresql+asyncpg://... PYTHONPATH=. \
        python scripts/run_missing_backtests.py

Exit 0 = ran & saved; 2 = no POSTGRES_URL. Prints a computed-vs-claimed table and
writes backend/backtest/results/missing_backtests_<UTC>.json. This does NOT mutate
the engine, configs, live paper books, or the DB — it is a read-only backtest that
writes ONE result file.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

os.environ.setdefault("PYTHONHASHSEED", "0")
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))


def _num(x) -> float | None:
    return None if x is None else float(x)


async def _run() -> list[dict]:
    from backend.backtest.configs import defensive, enhanced_fplus
    from backend.backtest import runner as R
    from backend.db.session import SessionLocal
    from scripts.gauntlet_lib import FULL2, cfg_fplus, covid_crash_drawdown

    _, start, end, floor = FULL2  # ("FULL 2021-26", 2021-06-01, 2026-05-26, 2021-05-26)

    specs = [
        # (display name, engine label, config, site claim)
        ("Quant (Enhanced F+)", "enhanced_fplus() top_n=25",
         enhanced_fplus(start, end, floor),
         "+129.97% / 14.05% DD / 0.95 Sharpe"),
        ("Concentrated (top-10)", "Enhanced F+ top_n=10",
         cfg_fplus(start, end, floor, momentum_mode="voladj",
                   cash_yield_annual=Decimal("0.065"), top_n=10),
         "+152.66% / 12.63% DD / ~21% COVID"),
        ("Defensive", "defensive() lowvol+defensive_exposure",
         defensive(start, end, floor),
         "+84.61% / 17.63% DD / ~9% COVID"),
    ]

    out: list[dict] = []
    async with SessionLocal() as sess:
        for name, engine_label, cfg, claim in specs:
            print(f"\n>>> running {name} ({engine_label}) {start}..{end} ...", flush=True)
            r = await R.run_backtest(sess, cfg)
            row = {
                "name": name,
                "engine": engine_label,
                "top_n": getattr(cfg, "top_n", None),
                "total_return_pct": _num(r.total_return_pct),
                "cagr_pct": _num(r.cagr_pct),
                "max_drawdown_pct": _num(r.max_drawdown_pct),
                "sharpe": _num(r.sharpe),
                "total_trades": r.total_trades,
                "nifty500_tri_return_pct": _num(r.nifty500_tri_return_pct),
                "alpha_vs_nifty500_tri_pct": _num(r.alpha_vs_nifty500_tri_pct),
                "end_value": _num(r.end_value),
                "covid_crash_dd_pct": _num(covid_crash_drawdown(r.equity_curve)),
                "site_claim": claim,
            }
            out.append(row)
            print(f"    tot {row['total_return_pct']}%  maxDD {row['max_drawdown_pct']}%  "
                  f"Sharpe {row['sharpe']}  trades {row['total_trades']}  "
                  f"vs claim: {claim}", flush=True)
    return out


def main() -> int:
    if not os.environ.get("POSTGRES_URL"):
        print("CANNOT RUN: POSTGRES_URL is not set (needs the price DB reachable).",
              file=sys.stderr)
        return 2

    from scripts.gauntlet_lib import FULL2
    _, start, end, floor = FULL2

    results = asyncio.run(_run())

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Source the Concentrated/Defensive site cards + reproduce Quant. Audit 2026-07-08.",
        "window": {"start": start.isoformat(), "end": end.isoformat(),
                   "floor": floor.isoformat() if isinstance(floor, date) else None},
        "caveats": [
            "Survivorship bias: `stocks` universe has 0 delisted rows -> absolute returns optimistic.",
            "Only the delta vs frozen F+ on the SAME universe is fully fair.",
        ],
        "results": results,
    }

    outdir = _ROOT / "backend" / "backtest" / "results"
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outfile = outdir / f"missing_backtests_{stamp}.json"
    outfile.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("\n" + "=" * 78)
    print(f"{'strategy':<24}{'tot%':>9}{'maxDD%':>9}{'Sharpe':>8}{'trd':>6}{'covDD%':>8}   site claim")
    print("-" * 78)
    for r in results:
        print(f"{r['name']:<24}{r['total_return_pct']:>9}{r['max_drawdown_pct']:>9}"
              f"{str(r['sharpe']):>8}{r['total_trades']:>6}"
              f"{str(r['covid_crash_dd_pct']):>8}   {r['site_claim']}")
    print("=" * 78)
    print(f"SAVED -> {outfile}")
    print("Compare the computed numbers above to the site cards. If they differ, the "
          "site figures were never sourced — update strategies/page.tsx to match these, "
          "or gate the cards.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

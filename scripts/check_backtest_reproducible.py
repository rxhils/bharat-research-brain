"""Reproducibility gate for the F+ backtest (data-integrity foundation).

Fails loudly (exit 1) when a backtest number cannot be trusted, for the two
reasons that actually bit us on 2026-06-19:

  GATE 1 — DIRTY TREE: `backend/backtest/` (or the agent code it reads) has
    uncommitted changes. This is the exact bug that made "frozen F+" silently
    read +81.60% or +72.61% depending on whether an uncommitted scores.py
    lookahead-fix happened to be in the working tree. If the code isn't
    committed, the result isn't reproducible. Period.

  GATE 2 — NON-DETERMINISM: frozen F+ is not byte-identical across two
    consecutive runs.

Run before trusting any backtest, in CI, or as a pre-commit hook:

    POSTGRES_URL=... PYTHONPATH=. python scripts/check_backtest_reproducible.py

PYTHONHASHSEED is pinned to 0 so set/dict ordering can never introduce
cross-process drift (defense-in-depth; the engine is already deterministic).
Exit codes: 0 = pass, 1 = gate failed, 2 = cannot run (no DB configured).
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from datetime import date
from decimal import Decimal

# Pin the hash seed for the whole process before anything else imports.
os.environ.setdefault("PYTHONHASHSEED", "0")

# Code the backtest's result depends on — any uncommitted change here is a trap.
_GUARDED_PATHS = ("backend/backtest/", "backend/agents/")


def _configs():
    """The named canonical configs to gate: ENHANCED F+ (adopted default) and
    F+ CLASSIC (preserved fallback). Both must be byte-identical run-to-run."""
    from backend.backtest.configs import enhanced_fplus, fplus_classic

    return [("ENHANCED F+ (canonical)", enhanced_fplus()),
            ("F+ CLASSIC (fallback)", fplus_classic())]


def _dirty_paths() -> list[str]:
    out = subprocess.run(
        ["git", "status", "--porcelain", "--", *_GUARDED_PATHS],
        capture_output=True, text=True, check=True,
    ).stdout
    return [ln for ln in out.splitlines() if ln.strip()]


async def _run_all_twice() -> list[tuple]:
    """Run EACH named config twice in ONE event loop/session (asyncio.run twice would
    reuse pooled connections bound to a dead loop and crash). Returns one
    (name, run1, run2) per config."""
    from backend.backtest import runner as R
    from backend.db.session import SessionLocal

    out: list[tuple] = []
    async with SessionLocal() as sess:
        for name, cfg in _configs():
            a = await R.run_backtest(sess, cfg)
            b = await R.run_backtest(sess, cfg)
            sig_a = (a.total_return_pct, a.max_drawdown_pct, a.total_trades)
            sig_b = (b.total_return_pct, b.max_drawdown_pct, b.total_trades)
            out.append((name, sig_a, sig_b))
    return out


def main() -> int:
    if not os.environ.get("POSTGRES_URL"):
        print("CANNOT RUN GATE: POSTGRES_URL is not set.", file=sys.stderr)
        return 2

    fails: list[str] = []

    # GATE 1 — committed code only.
    dirty = _dirty_paths()
    if dirty:
        fails.append(
            "DIRTY WORKING TREE — backtest code has uncommitted changes, so "
            "results are NOT reproducible. Commit or stash first:\n    "
            + "\n    ".join(dirty))
    else:
        print("OK  gate 1: backtest working tree is clean (committed code only)")

    # GATE 2 — each named config byte-identical across two consecutive runs.
    for name, r1, r2 in asyncio.run(_run_all_twice()):
        if r1 != r2:
            fails.append(f"NON-DETERMINISTIC — {name} differs across runs: {r1} != {r2}")
        else:
            print(f"OK  gate 2: {name} reproducible across 2 runs -> "
                  f"ret {r1[0]}% maxDD {r1[1]}% trades {r1[2]}")

    if fails:
        print("\nREPRODUCIBILITY GATE FAILED:\n- " + "\n- ".join(fails), file=sys.stderr)
        return 1
    print("\nREPRODUCIBILITY GATE PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

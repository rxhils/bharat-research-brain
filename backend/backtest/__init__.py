"""Walk-forward backtest harness (Phase 5, Chunk 5.2).

Read-only against `prices_eod_adjusted` — never writes to live signal tables.
Approach B (price-only technical reconstruction): the live ranking score depends
on tables that are not stored per-date historically (fundamentals/FII/sector/
sentiment/macro/delivery/vcp), so the backtest reconstructs a technical-only
score from price bars dated <= D and validates THAT alone. No lookahead.
"""

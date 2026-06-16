# Architecture

How `bharat-research-brain` is layered and how data moves through it. This is the
narrative companion to the diagram in the [README](../README.md); for a file-by-file
map see [STRUCTURE.md](STRUCTURE.md), and for *why* the strategy is shaped the way it
is see [VALIDATION.md](VALIDATION.md).

---

## The three layers

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1 — Nightly research agents                          │
│  price · technical · fundamentals · news · sentiment ·      │
│  sector · FII/DII · macro · risk                            │
│                         │ each writes signals + cited claims │
│                         ▼                                    │
│  Ranking agent → 0–100 composite score per stock            │
│                         │                                    │
│                         ▼                                    │
│  Meta-Auditor → rejects any claim without evidence          │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2 — The F+ strategy engine (frozen, validated)       │
│  quality gate → weekly cash lever → breakdown stops →       │
│  sized, sector-capped, cash-managed target book             │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3 — Forward paper-trading tracker                    │
│  runs frozen F+ on Rs 10L with genuine cash accounting,     │
│  append-only ledger, daily mark-to-market                   │
└─────────────────────────────────────────────────────────────┘
        Postgres = canonical numbers   ·   Obsidian vault = canonical prose
```

### Layer 1 — Research agents → composite score

Each agent inherits `BaseAgent` and returns an `AgentOutput` carrying `claims`
(text + evidence + confidence), `metrics`, `vault_writes`, and `errors`. Agents are
single-responsibility and mostly event/schedule-driven:

- **universe** — the ~507-stock investable set; ISIN is the canonical key.
- **price** / **adjusted_price** — EOD OHLCV ingest and split/bonus adjustment. All
  technical math runs on the adjusted series (a wrong adjustment fabricates breakouts).
- **technical** — RSI, MACD, EMA, ATR, volume features.
- **fundamentals** — yfinance financials, FCF, quarterly trend.
- **news** + **sentiment** — whitelisted feeds scored locally by FinBERT.
- **sector**, **fii_dii**, **macro**, **risk** — sector tilt, institutional flows,
  VIX/FX regime, per-stock risk penalty.
- **ranking** — merges the component scores into a single 0–100 composite.
- **meta_auditor** — the fact-checker. It fails closed: claims with no evidence,
  contradictory confidence, or stale data (>1h during market hours) are rejected
  before anything is published.

The merged composite (the technical + momentum core, plus whatever components have
historical coverage) is the signal the strategy consumes.

### Layer 2 — The F+ engine

F+ lives in `backend/backtest/` (`engine.py`, `runner.py`, `scores.py`). It is
**frozen** — validated and not modified by ongoing work. Given daily scores it
produces a target portfolio through three mechanisms:

1. **Quality gate** — restrict to a quality set (low-vol proxy pre-2024), 25 names,
   max 4 per sector, quarterly name rebalance with a hold-winners buffer.
2. **Weekly cash lever** — a decoupled 5-day exposure check that scales the book to
   100% / 50% / 25% invested based on a market-regime read. *This is the piece that
   caught COVID* — it cut exposure before the 23-Mar-2020 bottom, where the quarterly
   version (Config F) reacted two months late.
3. **Breakdown stops** — sell a holding the day it falls >15% from entry or fails
   quality; freed capital sits in cash until the next rebalance.

Configs A–F are byte-identical earlier rungs: F+'s two new behaviors
(`exposure_check_days`, `breakdown_exit_pct`) default OFF, so enabling them is the
*only* difference. That invariant is locked by a regression test.

### Layer 3 — Forward paper tracker

`backend/paper/` runs the frozen F+ engine *forward* as an out-of-sample paper
portfolio. It calls F+'s decision functions verbatim and executes them against real
EOD prices with genuine cash accounting across four append-only tables
(`paper_account`, `paper_position`, `paper_equity_curve`, `paper_event_log`). Ops:
`inception`, `daily_mark`, `weekly_exposure`, `quarterly_rebalance` — self-triggered
by trading-day count and idempotent. `scripts/nightly_run.py` is the 24/7 driver.

---

## Data flow (one direction)

```
NSE bhavcopy / yfinance / news feeds / FII-DII CSVs
        → ingest agents → Postgres (prices_eod, *_adjusted, *_signals, …)
        → ranking agent → composite score per stock per day
        → Meta-Auditor (evidence gate)
        → F+ engine → target book (names + exposure + cash)
        → paper tracker → equity curve + event log
        → Obsidian vault (daily report, lessons) + dashboard
```

There is no feedback loop from execution back into scoring — the engine consumes
scores, it does not edit them.

---

## Two stores, two jobs

| Store | Canonical for | Examples |
|---|---|---|
| **PostgreSQL 16** | Structured / transactional numbers | prices, scores, signals, paper ledger |
| **Obsidian vault** | Human-readable prose & lessons | daily research notes, post-mortems, decisions |

If the two disagree, the **database wins for numbers** and the **vault wins for
narrative**. They are reconciled via migration, never a hack. All vault access goes
through `services/vault.py` so the frontmatter contract and atomic writes are enforced
in one place.

---

## Hard architectural constraints

These are enforced, not aspirational (full list in [`CLAUDE.md`](../CLAUDE.md) §2):

- **No order-placement code** anywhere — read-only broker APIs only.
- **No advisory language** in any output; every claim cites a source.
- **No NSE scraping** — only downloadable bhavcopies, broker APIs, and whitelisted feeds.
- **Money is `Decimal`**, never float. **Datetimes are timezone-aware** (IST display,
  UTC storage).
- **Backtests filter the point-in-time universe** and never use today's constituents
  to judge a past period (survivorship discipline).

# Contributing / Dev notes

This is a single-operator personal research project. These notes exist so that
"future-you" (and any AI assistant) can work on it safely. The authoritative rules
live in [`CLAUDE.md`](CLAUDE.md) (Claude Code) and [`AGENTS.md`](AGENTS.md) (Codex) —
this file is the short, practical version.

---

## Running tests and lint

The full suite runs in the backend container (dev tools are baked into the image):

```bash
# Tests
docker compose run --rm backend pytest -q

# Lint + format check
docker compose run --rm backend ruff check .

# Types
docker compose run --rm backend mypy backend
```

Or, with a local virtualenv and dependencies installed:

```bash
pytest -q
ruff check .
mypy backend
```

A change is not done until tests pass and `ruff` is clean.

---

## The disciplines that matter here

This is a backtesting project, so the integrity rules are not optional — they are the
difference between a real result and a fooled-yourself result.

### 1. No-lookahead

Every backtest read filters `trade_date <= D`, and the decision at day `D` uses
`closes[-2]` (yesterday's close), not `D`'s own close. Backtest code is **read-only**
against `prices_eod_adjusted` and never writes a live table. Sanity asserts fire on
suspicious output (e.g. any window CAGR > 40%, any single winner > +100%) — treat a
fired assert as a likely leak until proven otherwise.

### 2. Survivorship discipline

Backtests must filter the **point-in-time** universe (`effective_from <= trade_date <
effective_to`). Never judge a past period with today's constituents. Where a true
historical universe isn't available, say so — the current 2017–2020 study is
survivorship-biased (~400 of today's survivors), which makes results *optimistic*, and
that caveat is stated everywhere it appears.

### 3. Pre-registered bars

Decide a strategy's pass/fail thresholds **before** running it, write them down, and
hold them without post-hoc tuning. Tuning parameters to one observed crash is
curve-fitting, not validation. See [docs/VALIDATION.md](docs/VALIDATION.md) for how
configs A–F+ were judged this way.

### 4. The F+ engine is frozen

`backend/backtest/engine.py`, `runner.py`, and `scores.py` carry the validated F+
logic. Configs A–F are **byte-identical** earlier rungs; F+'s two extra behaviors
(`exposure_check_days`, `breakdown_exit_pct`) default OFF and are locked by a
regression test. Do not change this logic as a side effect of unrelated work. If you
genuinely need to evolve the strategy, that is a new, explicitly-scoped config — not an
edit to the frozen one.

### 5. Honesty in outputs

No advisory language ("buy"/"sell"/"guaranteed"), every claim cites a source, and every
report ends with the disclaimer block. The Meta-Auditor enforces this in the pipeline —
keep its job easy. Don't inflate results: F+ matches the index with less drawdown, it
does not beat the market on raw return.

---

## Scope lock

When given a chunk-scoped task, do **only** that chunk. Don't refactor unrelated files,
don't "improve" adjacent systems, don't add unrequested features. If you spot something
worth changing outside scope, write it to the follow-ups log in `AGENTS.md` (§16) and
stop. The operator approves scope changes explicitly.

## GateGuard

This repo is set up to work well with the GateGuard pre-edit gate: before the first
edit to a file it asks you to present concrete facts (who imports it, what it affects,
the data schema, the verbatim instruction). The point is to *investigate before
editing* rather than guess. Let the gate fire; don't pre-answer it. To disable it for a
setup/repair session, start with `ECC_GATEGUARD=off`.

---

## Coding conventions (the short list)

Full version in `CLAUDE.md` §8. The ones that bite if ignored:

- **Money is `Decimal`**, never `float`. Round half-even.
- **Datetimes are timezone-aware** — IST for display, UTC for storage.
- **Async-first** for all I/O; wrap CPU-bound sync work in `asyncio.to_thread`.
- **Type hints required**; `from __future__ import annotations` at the top of each file.
- **Structured logging** via `structlog` — no `print()`.
- **No secrets in code or git.** Use `.env` (gitignored); `.env.example` holds names only.
- Every agent has at least one happy-path test with mocked external calls.

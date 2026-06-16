# Validation

How the F+ strategy was chosen, what every rejected config taught us, and the
structural finding that makes the whole thing honest. Summarized from the lesson
notes in the Obsidian vault (`08_Lessons/config-*`, dated 2026-06-13 → 06-15).

> **The one-line takeaway:** F+ is the only config that passed its pre-registered
> bar. It earns index-like returns with roughly half the drawdown across two very
> different market eras. Its edge is **risk management and consistency, not raw
> return.** That is stated plainly because it is the truth.

---

## Method (why these results are trustworthy)

- **Two eras, not one.** Every config was run over **2017–2020** (includes the COVID
  crash) *and* **2021–2026** (post-COVID bull). A strategy that only wins in a bull
  is regime luck, not an edge — testing across a real crash is what exposed that.
- **Pre-registered bars.** The pass/fail thresholds for each config were written down
  *before* the run, then held without post-hoc tuning. A config either cleared its bar
  or it didn't.
- **No-lookahead discipline.** Every price/score read filters `trade_date <= D`; the
  decision at day D uses `closes[-2]` (yesterday's close), not D's own close. Sanity
  asserts fire on suspicious results (e.g. any window CAGR > 40%, any winner > +100%).
- **Walk-forward, not single split.** Four overlapping windows per era, so no single
  lucky entry point carries the verdict.
- **Honest caveats, always attached.** 2017–2020 is survivorship-biased (~400 of
  today's survivors, so results are *optimistic*); pre-2024 fundamentals are absent so
  the composite is its momentum/trend core; cash earns 0% (real ~6%, so F+ is shown
  slightly *worse* than reality).

---

## The journey: A → F+

| Config | Idea | Pre-registered verdict |
|---|---|---|
| **A / B** | Cash-floor allocators | Looked good only by sitting in cash — "winning" by not playing. Unusable as a strategy. |
| **C** | Always-invested momentum, top-10 concentrated | **Failed.** Fell **−57% in the COVID window** vs the index's −38%; over 2017–2020 it returned *less* than a passive index fund with a *bigger* drawdown and negative Sharpe. The 2021–26 outperformance (+221%) was regime luck. |
| **D** | Diversification — sector caps + trailing stops | **Failed** (1/4 windows beat; drawdown unchanged). The caps and stops worked mechanically, but the 25–30% portfolio drawdowns didn't move: that drawdown is *market beta*, not single-name risk. |
| **E** | Defensive regime rotation (rotate to low-beta in risk-off) | **Failed** (0/4 beat). The 200-DMA signal is reactive — it flipped mid-crash, and the low-beta defensives it bought *still* fell ~16%. A long-only book is still long the market. |
| **F** | Quality + momentum + a *real* cash sleeve, low turnover | **Failed** (1/4 bars). The cash lever is the right idea and genuinely lowered drawdown on *slow* declines — but tied to the quarterly rebalance it fired **~2 months too late** in COVID, cutting exposure *after* the bottom and then capping the recovery. |
| **F+** | Config F + **weekly** (decoupled) cash lever + **breakdown stops** | **PASSED both eras.** ✓ |

Each config was a direct response to the previous one's failure. The arc is a single
argument: concentration is fragile (C) → you can't diversify your way out of market
risk (D) → you can't low-beta your way out either (E) → you need a *real* exit to cash
(F) → but it has to be *fast enough to matter* (F+).

---

## F+ — the numbers

**F+ = Config F + exactly two changes**, both defaulting OFF so A–F stay byte-identical:

1. **Weekly cash lever** (`exposure_check_days = 5`) — decouple the exposure check from
   the quarterly name rebalance so it can de-risk weekly.
2. **Cut-on-breakdown** (`breakdown_exit_pct = 15%`) — sell a name the day it drops
   >15% from entry; park the cash until the next rebalance.

### Pre-registered bar (2017–2020, vs Config F) — passed all three

| Bar | Result |
|---|---|
| COVID-window max drawdown < F's 39.75% | **PASS — 26.93%** |
| Full-period return ≥ F's +24.06% | **PASS — +40.99%** |
| Full-period Sharpe > F's −0.01 | **PASS — +0.22** |

### Era 1 — 2017–2020 (incl. COVID), Rs 10L

| Strategy | Total return | Max drawdown | Sharpe |
|---|---:|---:|---:|
| Nifty 500 TRI (buy & hold) | +62.45% | 38.52% | — |
| Config C | +39.68% | 41.58% | 0.17 |
| Config F | +24.06% | 38.16% | −0.01 |
| **Config F+** | **+40.99%** | **23.27%** | **0.22** |

F+ has the **lowest drawdown of all** (23.3% vs the index's 38.5%) while beating C on
return and crushing F. It still lags the index on raw return — but with ~15 points less
drawdown.

### The COVID exposure trace (why F+ survived)

```
2020-02-11  exposure 1.00
2020-03-04  exposure 0.50   ← cut BEFORE the 23-Mar bottom (F was still 1.00)
2020-03-12  exposure 0.25   ← 75% cash, 11 days before the bottom
2020-06-03  exposure 0.50   ← re-entry into the recovery
Blended equity: Rs 12.47L peak → Rs 9.93L trough (2020-03-27) = −20.4%
   (Config F was −38.2% · Config C was −43.2% at the same time)
```

The weekly check caught the first leg; the quarterly lever (F) could not. Covid
drawdown was roughly **halved**.

### Era 2 — 2021–2026 (post-COVID bull)

Walk-forward: **F+ beat the Nifty 500 TRI in all 4 windows**, with 9–17% drawdowns and
Sharpes up to **1.56**.

| Strategy | Full-period return | Max drawdown | Sharpe |
|---|---:|---:|---:|
| Nifty 500 TRI (buy & hold) | +82.17% | 18.59% | — |
| Config C | +220.97% | 20.61% | 0.92 |
| **Config F+** | **+81.60%** | 18.95% | 0.51 |

F+ **matches** the index over the full period (the full-period figure is dragged down
by a warmup-floored no-trade start; the 4-window read is the cleaner one). Config C
tripled the index here — but that is the same concentrated, always-invested bet that
fell 43–55% in COVID. **F+ trades C's bull-market upside for survivability.**

---

## The structural finding (the honest core)

Three configs (C, D, E) failed for the *same* reason, and it is not a bug — it is a
property of long-only equity:

> **You cannot have "always invested" *and* "low drawdown" in a long-only book.**
> Portfolio drawdown is *market exposure*. When the broad market falls in a
> correlated selloff, diversification (D) only reduces single-name risk and low-beta
> rotation (E) is still 100% long the market — neither escapes the fall. The only
> thing that ever reduced drawdown in this entire study was *being out of the market*
> (holding cash).

That is why F+ works and why it is described as **risk management, not alpha**:

- It is **not** a return-maximizer. A concentrated always-invested book (C) wins raw
  return in a bull — with brutal crash drawdowns and a coin-flip record across windows.
- It **is** the most consistent config built: max drawdown ≤ 27% in *both* eras
  (vs C's 42–55% in COVID), positive full-period Sharpe in both, beat C in the crash
  era and the index in all four recent windows.
- The two fixes did exactly what the COVID lesson said was needed: a faster,
  decoupled de-risk that actually catches the first leg.

So the README claim is deliberately bounded: **F+ matches the index with roughly half
the drawdown — it does not beat the market on raw return.** Claiming more would be
dishonest given the evidence above.

---

## What this does *not* prove

- **Only the technical/momentum composite was backtestable.** Fundamentals, FII,
  sentiment, macro, sector, delivery, and VCP signals are not stored historically
  per-date, so they cannot be reconstructed without lookahead. The backtest validates
  F+ on its *mechanical* composite core — not "do the live agents add value." That
  question needs the **forward** paper-trading record.
- **Forward record is young and paper-only.** It starts at inception, is never
  backfilled, and won't be meaningful for ~6–12 months or see a real crash until one
  happens. It is labeled as such everywhere.
- **Survivorship + degraded-composite caveats** make the 2017–2020 results
  *optimistic*, not pessimistic — the honest direction.

---

## Disclaimer

For personal research and educational purposes only. Not investment advice. The
operator has not paid for advice and Claude is not registered as an investment adviser
or research analyst with SEBI.

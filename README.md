<p align="center">
  <img src="assets/banner.png" alt="Bharat Research Brain" width="520" />
</p>

<h2 align="center">Bharat Research Brain</h2>
<h4 align="center">Autonomous equity research engine for Indian markets</h4>

<p align="center">
  507 NSE/BSE stocks &nbsp;·&nbsp; 14 agents &nbsp;·&nbsp; Ranked daily &nbsp;·&nbsp; Cited reports &nbsp;·&nbsp; Fully local &nbsp;·&nbsp; ₹0/month
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python" />
  <img src="https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql" />
  <img src="https://img.shields.io/badge/FastAPI-async-009688?style=flat-square&logo=fastapi" />
  <img src="https://img.shields.io/badge/Docker-compose-2496ED?style=flat-square&logo=docker" />
  <img src="https://img.shields.io/badge/FinBERT-local-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/Tests-311%20passing-brightgreen?style=flat-square" />
</p>

---

## What it does

Every evening at **18:30 IST**, Bharat Research Brain runs a 14-agent pipeline that ingests market data, computes signals, and ranks all 507 Indian stocks on a 0–100 composite score. By 7:00 AM you have:

- A **ranked watchlist** — 507 stocks scored, top tier flagged `bullish-watch`
- A **cited research note** — macro regime, top setups, sector rotation, risk flags, every claim backed by data
- Instant **stock deep-dives** — `bharat analyze SUNPHARMA` returns 9 sections in under 2 seconds

Everything runs on your own machine. No subscriptions, no cloud API bills, no data leaving your system.

---

## Current numbers

| Metric | Value |
|--------|-------|
| Stocks in universe | 507 (Nifty 500 + Midcap 150) |
| Price rows (adjusted) | 522,677 |
| Trading days loaded | 1,229 |
| Corporate events | 2,898 (splits + dividends) |
| DB migrations | 23 |
| DB tables | 21 |
| Git commits | 44+ |
| Tests passing | 311 |
| Pipeline duration | ~154 seconds |
| Monthly cost | ₹0 |

**Latest signal distribution:**

| Label | Count | Meaning |
|-------|-------|---------|
| `bullish-watch` | 15 | Score ≥ 75 — highest conviction |
| `needs-confirmation` | 187 | Score 55–74 |
| `neutral` | 209 | Score 40–54 |
| `cautious` | 88 | Score 20–39 |
| `avoid` | 8 | Score < 20 |

---

## The 14-agent pipeline

Each agent runs once nightly in sequence. One agent failing does not stop the rest.

```
Universe → Price → Adjusted Price → Technical → News → Sentiment
       → Fundamentals → Sector → FII/DII → Macro → Risk
       → Ranking → Report → Meta-Auditor
```

| # | Agent | What it does |
|---|-------|-------------|
| 1 | **Universe** | Validates all 507 stocks exist and flags any NSE/BSE index rebalancing |
| 2 | **Price** | Reads the NSE bhavcopy CSV and inserts OHLCV rows into PostgreSQL |
| 3 | **Adjusted Price** | Applies split/bonus correction factors to all historical prices |
| 4 | **Technical** | Computes RSI(14), EMA(20/50/200), MACD, ATR, volume signal, 52-week proximity, delivery % |
| 5 | **News** | Pulls headlines from 6 RSS feeds + Upstox News API, matches to stocks by symbol/name |
| 6 | **Sentiment** | Runs every headline through **local FinBERT** — no API call, bull/bear/neutral per article |
| 7 | **Fundamentals** | Fetches PE, ROE, D/E, FCF, quarterly P&L trends, dividend yield via yfinance |
| 8 | **Sector** | Classifies 507 stocks into 19 sectors, scores each as leading / neutral / lagging |
| 9 | **FII/DII** | Parses SEBI institutional flow data, computes 5-day rolling net signal per fund type |
| 10 | **Macro** | Reads India VIX, USD/INR, Brent crude, Nifty vs 200d EMA → outputs `risk-on / neutral / risk-off` |
| 11 | **Risk** | Computes per-stock penalty (0–15 pts) from ATR volatility, news spikes, earnings proximity, promoter pledges |
| 12 | **Ranking** | Combines all signals into a single 0–100 score, assigns signal label |
| 13 | **Report** | Writes a structured daily research note to PostgreSQL and your Obsidian vault |
| 14 | **Meta-Auditor** | Fact-checks every claim in the report against the database. Fail-closed: 5 rules, all must pass |

---

## The scoring formula

```
composite_score =
    (technical_score  × 0.35)   ← RSI zone, EMA stack, MACD, volume trend, 52-week proximity
  + (fundamental_score × 0.40)  ← PE (sector-relative), ROE, D/E, FCF, quarterly trend, dividends
  + (macro_score       × 0.25)  ← FII signal, sector signal, macro regime
  + sentiment_adj  (±5)         ← FinBERT per-stock news sentiment
  − risk_penalty   (0–15)       ← volatility, news spikes, earnings proximity, pledge flag

= composite_score (0–100, clamped)
```

**Why these weights?** Fundamentals carry the most weight (0.40) because sustainable edge in Indian mid/large caps comes from business quality. Technicals (0.35) capture timing. Macro (0.25) sets the regime. The formula will be replaced by a trained XGBoost model in Phase 5 once 90+ days of outcome data accumulates.

---

## What the Meta-Auditor checks

The report is rejected if any of these fail:

1. Every cited score must match the exact database value
2. Every cited headline must have a URL in the `news_articles` table
3. No banned advisory language ("buy", "sell", "guaranteed", "tip")
4. The disclaimer block must be present
5. All source dates must match what is in the database

`audit_passed = True` only when all 5 pass.

---

## Terminal deep-dive

```bash
bharat analyze SUNPHARMA
```

Returns in < 2 seconds, no external calls:

```
1. Stock snapshot       price, change, 52-week range, market cap
2. Technical signals    RSI, MACD, EMA stack (20/50/200 position)
3. Fundamentals         PE, ROE, FCF, D/E, quarterly trend
4. Sentiment            recent headlines + FinBERT scores
5. Sector context       is Pharma leading or lagging right now?
6. FII/DII flows        institutional money direction (5-day rolling)
7. Macro regime         risk-on / neutral / risk-off and why
8. Risk flags           volatility, news spikes, earnings proximity
9. Composite score      0-100 with component breakdown + conviction (1–5)
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11 |
| API server | FastAPI (async) |
| ORM + migrations | SQLAlchemy 2.0 + Alembic |
| Database | PostgreSQL 16 (pgvector + pg_trgm extensions) |
| Cache | Redis 7 |
| Containers | Docker Compose (WSL2 backend) |
| Local NLP | FinBERT — ProsusAI/finbert via transformers |
| Local LLMs | Ollama — qwen2.5:14b, llama3.1, mistral (Phase 6+) |
| Scheduler | APScheduler (inside FastAPI) |
| Knowledge base | Obsidian vault |
| Testing | pytest + ruff + mypy (strict) |
| Frontend | Next.js 14 (Phase 7 only) |

---

## Data sources

| Source | Data | How it enters |
|--------|------|--------------|
| NSE bhavcopy | Daily OHLCV for all 507 stocks | Operator download → file ingest |
| Yahoo Finance (yfinance) | PE, ROE, D/E, FCF, fundamentals | API (free) |
| Frankfurter API | USD/INR exchange rate | API (free) |
| SEBI FPI files | FII/DII institutional flows | Operator download → file ingest |
| Upstox News API | Stock-specific news per ISIN | API (free with account) |
| RSS (6 sources) | ET Markets, Mint, BS, Moneycontrol, NSE, BSE | feedparser |
| Moneycontrol | Delivery %, earnings calendar | Operator download → file ingest |

> NSE website scraping is prohibited by their Terms of Use. All NSE data enters via manually downloaded exchange-published files.

---

## Quickstart

**Prerequisites:** Docker Desktop (WSL2), Python 3.11, Git

```bash
# 1. Clone
git clone https://github.com/rxhils/bharat-research-brain.git
cd bharat-research-brain

# 2. Configure
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, DATABASE_URL, VAULT_PATH

# 3. Start services
docker compose up -d postgres redis

# 4. Run all 23 migrations
docker compose run --rm backend alembic upgrade head

# 5. Seed the 507-stock universe
docker compose run --rm backend python -m backend.cli universe run

# 6. Load price history (NSE bhavcopy files in data/)
docker compose run --rm backend python -m backend.cli price run --all

# 7. Run the full pipeline once
docker compose run --rm backend python -m backend.cli pipeline run

# 8. Analyze a stock
docker compose run --rm backend python -m backend.cli analyze RELIANCE
```

---

## CLI reference

```bash
# Stock research
bharat analyze SUNPHARMA
bharat analyze --isin INE002A01018

# Rankings
bharat ranking show --signal bullish-watch --limit 20
bharat ranking show --sector Pharma

# Pipeline
bharat pipeline run
bharat pipeline status --limit 5

# Individual agents
bharat price run
bharat technical run
bharat sentiment run --batch-size 32
bharat fundamentals run
bharat ranking run --all
bharat report show --date today

# Data ingest (operator-downloaded files)
bharat fii ingest --file data/fii_dii_clean.csv
bharat delivery ingest --file data/delivery_latest.csv
bharat earnings ingest --file data/earnings_calendar.csv
```

---

## Architecture

```
bharat-research-brain/
├── alembic/                 # 23 DB migrations (schema truth = SQLAlchemy models)
├── backend/
│   ├── agents/              # 14 signal agents
│   │   ├── universe.py      # 507-stock universe, ISIN as canonical key
│   │   ├── price.py         # NSE bhavcopy ingest
│   │   ├── adjusted_price.py# split/bonus correction engine
│   │   ├── technical.py     # RSI, MACD, EMA, ATR, volume
│   │   ├── news.py          # RSS + Upstox + bulk/block deal ingest
│   │   ├── sentiment.py     # FinBERT local scoring
│   │   ├── fundamentals.py  # yfinance + FCF + quarterly trends
│   │   ├── sector.py        # 19-sector classification + scoring
│   │   ├── fii_dii.py       # institutional flow signals
│   │   ├── macro.py         # VIX + FX + regime classifier
│   │   ├── risk.py          # per-stock risk penalty
│   │   ├── ranking.py       # 0-100 composite score + signal label
│   │   ├── report.py        # daily research note (deterministic template)
│   │   └── meta_auditor.py  # 5-rule fact checker, fail-closed
│   ├── db/
│   │   ├── models.py        # SQLAlchemy ORM (21 tables)
│   │   └── repositories/    # data access layer, no business logic
│   ├── services/
│   │   ├── vault.py         # Obsidian read/write (all vault I/O goes here)
│   │   ├── finbert.py       # local FinBERT sidecar client
│   │   └── alerts.py        # Telegram + email
│   ├── orchestration/
│   │   └── scheduler.py     # APScheduler — 18:30 IST M-F, 14 agents, 154s
│   └── cli.py               # Typer CLI entrypoint
├── services/finbert/        # FinBERT sidecar — FastAPI + transformers
├── data/                    # manually downloaded CSVs (gitignored)
└── scripts/                 # seed_universe.py, vault_migrate.py
```

---

## Database — 23 migrations, 21 tables

| Tables | Phase |
|--------|-------|
| stocks, prices, adjusted_prices, trading_calendar, index_constituents | Phase 1 |
| news_articles, fundamental_signals, sector_signals, fii_dii_flows | Phase 3 |
| macro_signals, risk_signals, stock_rankings, daily_reports, pipeline_runs | Phase 4 |
| promoter_signals, stock_vcp_signals | Phase 4.9–4.10 |
| delivery_signals, earnings_calendar | Phase 3.2b |
| outcome_log, xgboost_features | Phase 5 (planned) |

---

## Build phases

| Phase | Status | What it delivers |
|-------|--------|-----------------|
| 0 — Infrastructure | ✅ Done | Docker stack, Postgres 16, Redis, FastAPI, Ollama |
| 1 — Data spine | ✅ Done | 507-stock universe, 5yr price history, corporate events, adjusted prices |
| 2 — Live data | ✅ Done | Redis live feed, intraday VWAP / volume z-score signals |
| 3 — Analytics | ✅ Done | 6 signal agents (technical, news, sentiment, fundamentals, sector, FII/DII) |
| 3.2b — Data enrichment | ✅ Done | Upstox news, delivery signals, earnings calendar, real SEBI FPI data |
| 4 — Synthesis | ✅ Done | Macro agent, risk agent, ranking, report, Meta-Auditor, nightly scheduler |
| 4.9 — Signal quality | ✅ Done | India VIX regime override, 52-week proximity, sector-relative PE |
| 4.10 — VCP screener | ✅ Done | Minervini VCP screen → `stock_vcp_signals`, +10 pts in technical score |
| 4.11 — Sector ratios | 🔄 In progress | NIM/NPA for banks, EBITDA margin for pharma, USD revenue for IT |
| 4.12 — Market breadth | 🔄 In progress | A/D ratio, % stocks above EMA200, breadth-based regime override |
| 4.13 — Event patterns | ⏳ Planned | Sector responses to RBI moves, crude spikes, budget, elections |
| 4.14 — Zerodha live prices | ⏳ Planned | Replace demo feed with real intraday prices via Zerodha Kite |
| 5 — Outcomes + ML | ⏳ Planned | Outcome agent, walk-forward backtest, XGBoost weight learning |
| 6 — Hermes AI layer | ⏳ Planned | Conversational interface over the engine, self-learning agent memory |
| 7 — Dashboard | ⏳ Planned | Next.js UI — built only after Phase 5 proves signals work |

---

## Phase 5: Self-learning loop (planned)

The most important upcoming phase. After 30+ days of live runs:

1. **Outcome Agent** (15:45 IST daily) — compares yesterday's `bullish-watch` picks against today's actual closing prices. Logs accuracy per signal, per sector, per macro regime.
2. **Walk-forward backtest** — replays 2 years of history with India-accurate cost model (STT 0.1% both sides, exchange charges, SEBI fee, GST — ~0.35% round-trip). Benchmark: Nifty 50 buy-and-hold.
3. **XGBoost** — after 90+ days of outcomes, trains a model to replace the hardcoded weights. The scoring formula becomes fully data-driven.

Target: Sharpe > 1.0, max drawdown < 20%.

---

## Phase 6: Hermes conversational layer (planned)

A separate Python process that reads Bharat via HTTP — never touches Bharat's code.

```
Bharat (engine)              Hermes (intelligence)
FastAPI :8000          ←→    Python process
Postgres :5432         ←→    HTTP API calls only
Obsidian vault         ←→    Shared filesystem
```

Each agent gets a `memory.md` in the vault, updated nightly by the Outcome Agent with accuracy stats. Hermes reads all memories before each session. Agents are measurably smarter than yesterday.

---

## How it compares

| | Bharat Research Brain | Typical retail setup | Mid-tier PMS |
|--|---|---|---|
| Stocks covered | 507 | 20–50 manually | 50–200 |
| Data freshness | Next morning | Days / weeks | Real-time (paid) |
| Signal citation | Every claim cited | None | Partial |
| Cost | ₹0/month | ₹2k–₹10k/month | 1–2% AUM fee |
| Self-improving | Yes (Phase 5) | No | Rarely |
| Private | Fully local | Depends | No |

---

## Compliance

This system is for **personal research only.**  
Output is never used for advisory services.  
Not registered with SEBI as an investment adviser.  
No order-placement code exists anywhere in this repository.  
See `CLAUDE.md §2` for the full hard rules and personal-use scope lock.

---

## License

Private — personal research use only.

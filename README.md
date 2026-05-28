# Bharat Research Brain

> Autonomous multi-agent research engine for Indian equity markets.  
> Scores 507 NSE/BSE stocks nightly. Outputs ranked watchlists and  
> cited daily research reports. Runs locally — zero cloud, zero cost.

---

## What it does

Every evening at 18:30 IST, 14 agents run in sequence:

1. Downloads NSE bhavcopy (daily OHLCV for 507 stocks)
2. Applies split/bonus adjustments to all price history
3. Computes RSI, MACD, EMA 20/50/200, ATR, volume signals
4. Fetches news from 6 RSS feeds + Upstox News API
5. Scores every article with FinBERT (local, no API)
6. Fetches fundamentals — PE, ROE, FCF, quarterly trends
7. Classifies 19 sectors as leading / neutral / lagging
8. Ingests FII/DII institutional flow data
9. Reads macro signals — VIX, USD/INR, crude, Nifty vs 200d MA
10. Computes per-stock risk scores including earnings proximity
11. Ranks all 507 stocks 0–100 with a composite formula
12. Writes a structured daily research report
13. Fact-checks the report against the database (Meta-Auditor)
14. Saves everything to PostgreSQL + Obsidian vault

Output: `bharat analyze SUNPHARMA` gives a full 9-section  
terminal deep-dive in 2 seconds from the local database.

---

## Current state

| Metric | Value |
|--------|-------|
| Stocks in universe | 507 (Nifty 500 + Midcap 150) |
| Price history | 522,677 rows · 1,229 trading days |
| Agents | 14 |
| DB migrations | 23 |
| Tests passing | 311 |
| Pipeline duration | ~154 seconds |
| Monthly cost | ₹0 |

**Signal distribution (latest run):**

| Label | Count |
|-------|-------|
| bullish-watch | 15 |
| needs-confirmation | 187 |
| neutral | 209 |
| cautious | 88 |
| avoid | 8 |

---

## Ranking formula
```
composite = (technical × 0.35) + (fundamental × 0.40) + (macro × 0.25)
          + sentiment_adj (±5)
          - risk_penalty (0–15)
```

**Technical score** — RSI zone, EMA position, MACD, volume trend,  
52-week proximity, delivery % (institutional conviction signal)

**Fundamental score** — PE (sector-relative), ROE, D/E ratio, FCF,  
quarterly profit trend, dividend history, current ratio

**Macro score** — FII/DII 5-day rolling sum, sector momentum,  
macro regime (Nifty vs 200d MA + India VIX)

**Risk penalty** — ATR volatility, news spike, earnings proximity  
(days to next results), promoter pledge flag

---

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11 |
| API | FastAPI |
| ORM | SQLAlchemy 2.0 + Alembic |
| Database | PostgreSQL 16 (pgvector + pg_trgm) |
| Cache | Redis 7 |
| Containers | Docker Compose |
| NLP (local) | FinBERT — ProsusAI/finbert |
| LLM | DeepSeek API (Phase 6) |
| Scheduler | APScheduler |
| Knowledge base | Obsidian vault |

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/rxhils/bharat-research-brain.git
cd bharat-research-brain

# 2. Configure
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, DATABASE_URL

# 3. Start
docker compose up -d postgres redis

# 4. Run migrations
docker compose run --rm backend alembic upgrade head

# 5. Seed universe (507 stocks)
docker compose run --rm backend python -m backend.cli universe run

# 6. Download price history (NSE bhavcopy)
docker compose run --rm backend python -m backend.cli price run --all

# 7. Run full pipeline
docker compose run --rm backend python -m backend.cli pipeline run

# 8. Analyze a stock
docker compose run --rm backend python -m backend.cli analyze RELIANCE
```

---

## CLI commands

```bash
# Rankings
bharat ranking show --signal bullish-watch --limit 20
bharat ranking show --sector Pharma

# Stock deep-dive
bharat analyze SUNPHARMA
bharat analyze --isin INE002A01018

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

# Data ingest
bharat fii ingest --file data/fii_dii_clean.csv
bharat delivery ingest --file data/delivery_latest.csv
bharat earnings ingest --file data/earnings_calendar.csv
```

---

## Architecture

```
data/                   # manually downloaded CSVs (gitignored)
alembic/                # 23 DB migrations
backend/
  agents/               # 14 signal agents
    universe.py         # 507-stock universe validation
    price.py            # NSE bhavcopy downloader
    adjusted_price.py   # split/bonus correction engine
    technical.py        # RSI, MACD, EMA, ATR
    news.py             # RSS + deal ingest
    sentiment.py        # FinBERT scoring
    fundamentals.py     # yfinance fundamentals
    sector.py           # sector classification
    fii_dii.py          # institutional flows
    macro.py            # regime + VIX + FX
    risk.py             # per-stock risk scores
    ranking.py          # 0-100 composite score
    report.py           # daily research note
    meta_auditor.py     # 5-rule fact checker
    delivery.py         # delivery % signals
    earnings.py         # results calendar
  db/
    models.py           # SQLAlchemy ORM (schema truth)
    repositories/       # data access layer
  services/             # FinBERT, live feed, Redis
  orchestration/        # APScheduler pipeline
  cli.py                # Typer CLI entrypoint
scripts/
  download_permitted.py # Frankfurter + yfinance only
services/finbert/       # reserved (in-process instead)
```

---

## Data sources

| Source | Data | Method |
|--------|------|--------|
| NSE bhavcopy | Daily OHLCV | Operator download → file ingest |
| Yahoo Finance (yfinance) | Fundamentals, macro | API (free) |
| Frankfurter API | USD/INR | API (free) |
| SEBI FPI files | FII institutional flows | Operator download → file ingest |
| Upstox News API | Stock-specific news | API (free with account) |
| RSS feeds (6 sources) | Market news | feedparser |
| Moneycontrol | Delivery %, earnings calendar | Operator download → file ingest |

NSE scraping is prohibited by §2.5 of CLAUDE.md.  
All NSE data enters via manually downloaded files.

---

## Build phases

| Phase | Status | Description |
|-------|--------|-------------|
| 0 — Infrastructure | ✅ | Docker, Postgres, Redis, FastAPI |
| 1 — Data spine | ✅ | 507 stocks, 5yr prices, corp events |
| 2 — Live data | ✅ | Redis feed, intraday signals |
| 3 — Analytics | ✅ | 8 signal agents |
| 3.2b — News + data | ✅ | FII real data, delivery, earnings |
| 4 — Synthesis | ✅ | Ranking, report, auditor, scheduler |
| 4.10 — VCP screener | 🔄 | Minervini pattern detection |
| 4.11 — Sector ratios | 🔄 | NIM/NPA, ANDA, margins |
| 4.12 — Market breadth | 🔄 | A/D ratio, % above EMA200 |
| 5 — Outcomes + ML | ⏳ | Outcome agent, XGBoost |
| 6 — Hermes | ⏳ | Conversational AI layer |
| 7 — Dashboard | ⏳ | Next.js UI (after Phase 5) |

---

## Compliance

This system is for personal research only.  
Output is never used for advisory services.  
Not registered with SEBI as an investment adviser.  
See CLAUDE.md §1 for the full personal-use scope lock.

---

## License

Private — personal research use only.

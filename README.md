<p align="center">
  <img src="assets/banner.png" alt="Bharat Research Brain" width="480" />
</p>

<h3 align="center">Autonomous multi-agent research engine for Indian equity markets</h3>
<p align="center">
  Scores 507 NSE/BSE stocks nightly &nbsp;·&nbsp; Ranked watchlists &nbsp;·&nbsp; Cited daily reports &nbsp;·&nbsp; Runs locally — zero cloud, zero cost
</p>

---

## What is this?

Bharat Research Brain is a system that runs on your own computer every evening and automatically researches the Indian stock market for you. It looks at 507 stocks across the NSE and BSE — price movements, company financials, news sentiment, sector trends, and what big institutions are buying or selling — and distills all of it into a ranked list and a written research report by the time you sit down after dinner.

There is no subscription, no cloud service, and no ongoing cost. Everything runs locally. The only API that costs money is DeepSeek (used in a future phase for conversational queries) — for all current phases, the monthly bill is ₹0.

---

## How it works, step by step

Each evening at 18:30 IST, 14 agents run one after another in a pipeline. Here is exactly what each one does in plain language:

**1. Universe agent**
Confirms all 507 stocks are in the database. If NSE/BSE has added or removed a ticker, this agent flags it. Nothing proceeds until the universe is clean.

**2. Price agent**
Reads the NSE bhavcopy file (a CSV the exchange publishes daily with every stock's open, high, low, close, and volume). This file is downloaded manually by the operator — no scraping. The agent inserts new rows into the price history table. The database currently holds 522,677 rows covering 1,229 trading days.

**3. Adjusted price agent**
When a company does a stock split or a bonus issue, historical prices need to be corrected so charts don't show a false crash. This agent detects corporate events and applies backward-adjustment factors to all affected rows. Every price in the database is always split/bonus-adjusted.

**4. Technical agent**
For each of the 507 stocks, it computes:
- **RSI (14)** — is the stock overbought, oversold, or neutral?
- **MACD** — is momentum accelerating or decelerating?
- **EMA 20 / 50 / 200** — is the stock above its short, medium, and long-term trend lines?
- **ATR** — how volatile is the stock right now (daily range as % of price)?
- **Volume signal** — is today's volume above or below the 20-day average?
- **52-week proximity** — how close is the price to its annual high?
- **Delivery %** — what fraction of today's trades were delivery-based (institutional conviction proxy)?

**5. News agent**
Pulls the latest headlines from 6 RSS feeds (Economic Times Markets, Mint, Business Standard, Moneycontrol, NSE announcements, BSE announcements) and the Upstox News API. Headlines are matched to stocks by ticker symbol and company name.

**6. Sentiment agent**
Runs every matched headline through FinBERT — a financial language model that runs entirely on your local machine, no API call needed. Each headline is scored as positive, negative, or neutral with a confidence value. The agent aggregates these into a per-stock sentiment score and flags any stock that has had a sudden spike in negative news.

**7. Fundamentals agent**
Fetches PE ratio, ROE, debt-to-equity ratio, free cash flow, quarterly profit trend, dividend yield, and current ratio for each stock from Yahoo Finance (free). These are stored in the database and updated weekly.

**8. Sector agent**
Groups all 507 stocks into 19 sectors. For each sector, it computes the average technical and fundamental score of all its members and classifies the sector as **leading**, **neutral**, or **lagging**. This tells you which parts of the market have tailwinds and which have headwinds.

**9. FII/DII agent**
Ingests the daily FII (foreign institutional investors) and DII (domestic institutional investors) buy/sell data published by SEBI. Computes a 5-day rolling net flow for both. When foreigners are consistently net sellers and domestics are buying, that's a very different signal than both buying together.

**10. Macro agent**
Reads four macro indicators:
- **India VIX** — the market's fear gauge. Above 20 = spike, forces risk-off regardless of everything else.
- **USD/INR** — a rising rupee is generally supportive; a falling rupee adds cost pressure for import-heavy sectors.
- **Crude oil price** — impacts aviation, paints, tyres, petrochemicals, logistics.
- **Nifty vs its 200-day EMA** — the single most reliable bull/bear regime indicator. Above = risk-on. Below = risk-off.

The macro agent outputs one of three regime labels: `risk-on`, `neutral`, or `risk-off`. This label affects every stock's final score.

**11. Risk agent**
For each stock, computes a risk penalty (0–15 points subtracted from the final score) based on:
- ATR volatility (how wild the daily price swings are)
- News spike flag (sudden surge in negative headlines)
- Earnings proximity (days until the next quarterly results — stocks near results are riskier)
- Promoter pledge flag (if promoters have pledged shares as collateral, that's a red flag)

**12. Ranking agent**
Combines everything into one 0–100 composite score per stock:

```
composite = (technical × 0.35) + (fundamental × 0.40) + (macro × 0.25)
          + sentiment_adj (±5)
          - risk_penalty (0–15)
```

Then assigns a signal label:

| Score | Label |
|-------|-------|
| 75–100 | `bullish-watch` |
| 55–74 | `needs-confirmation` |
| 40–54 | `neutral` |
| 20–39 | `cautious` |
| 0–19 | `avoid` |

**13. Report agent**
Writes a structured daily research note in Markdown. It covers: market regime summary, top 15 bullish-watch stocks with reasoning, sector rotation analysis, macro outlook, FII/DII flow interpretation, stocks with notable news, and a risk calendar (upcoming earnings). The report is saved to PostgreSQL and exported to your Obsidian vault.

**14. Meta-Auditor agent**
Reads the report and checks every factual claim against the database. It enforces 5 rules:
1. Every cited score must match the database value.
2. Every cited news headline must exist in the news table with a URL.
3. No banned advisory language ("buy", "sell", "guaranteed", "tip").
4. The disclaimer block must be present.
5. No claims about the future without appropriate hedging language.

If any check fails, the report is flagged and the operator is notified.

---

## What you get at the end

```bash
bharat analyze SUNPHARMA
```

This returns a 9-section terminal deep-dive in under 2 seconds, entirely from the local database — no external calls at query time:

1. Stock snapshot (price, change, 52-week range)
2. Technical signal breakdown (RSI, MACD, EMA stack)
3. Fundamental snapshot (PE, ROE, FCF, D/E)
4. Sentiment summary (recent headlines + scores)
5. Sector context (is Pharma leading or lagging?)
6. FII/DII flow context
7. Macro regime impact
8. Risk flags
9. Composite score with component breakdown

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

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11 |
| API server | FastAPI |
| ORM | SQLAlchemy 2.0 + Alembic |
| Database | PostgreSQL 16 (pgvector + pg_trgm) |
| Cache | Redis 7 |
| Containers | Docker Compose |
| NLP (local) | FinBERT — ProsusAI/finbert |
| LLM | DeepSeek API (Phase 6 only) |
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

# 3. Start services
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

## CLI reference

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
```

---

## Data sources

| Source | Data | Method |
|--------|------|--------|
| NSE bhavcopy | Daily OHLCV | Operator download → file ingest |
| Yahoo Finance (yfinance) | Fundamentals, macro | API (free) |
| Frankfurter API | USD/INR | API (free) |
| SEBI FPI files | FII/DII flows | Operator download → file ingest |
| Upstox News API | Stock-specific news | API (free with account) |
| RSS feeds (6 sources) | Market news | feedparser |
| Moneycontrol | Delivery %, earnings calendar | Operator download → file ingest |

NSE scraping is prohibited. All NSE data enters via manually downloaded files.

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
| 4.11 — Sector ratios | 🔄 | NIM/NPA for banks, ANDA for pharma |
| 4.12 — Market breadth | 🔄 | A/D ratio, % stocks above EMA200 |
| 5 — Outcomes + ML | ⏳ | Outcome agent, XGBoost signal validation |
| 6 — Hermes | ⏳ | Conversational AI layer (DeepSeek) |
| 7 — Dashboard | ⏳ | Next.js UI (after Phase 5) |

---

## Compliance

This system is for personal research only.  
Output is never used for advisory services.  
Not registered with SEBI as an investment adviser.  
See `CLAUDE.md §1` for the full personal-use scope lock.

---

## License

Private — personal research use only.

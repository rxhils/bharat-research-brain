# CLAUDE.md — Indian Stock Research Intelligence System

> This file is read by Claude Code at the start of every session. It is the single
> source of truth for project context, hard rules, and conventions. Keep it
> current. Do not delete sections without reason.

---

## 1. Project identity

**Name:** `bharat-research-brain` (working name)

**What it is:** A 24/7 multi-agent research system for the Indian equity markets
(NSE/BSE). It ingests market data, news, fundamentals, technicals, sector signals,
macro indicators, and FII/DII flows, then produces ranked watchlists, daily
research reports, and an auditable knowledge graph in Obsidian.

**What it is NOT:**
- Not a trading bot. No order placement code in this repo, period.
- Not a financial-advisory product. No public alerts, no recommendations.
- Not a SEBI-registered algo platform. We are below the personal-use threshold.
- Not a SaaS. This runs on the operator's machine, for the operator's research.

**Operator:** Single user, personal research use, paper-trading only.

---

## 2. Hard rules (non-negotiable)

These rules override convenience, performance, and feature requests. If a request
conflicts with one of these, refuse and explain. If unclear, ask.

1. **No order-placement code.** No broker `place_order`, `modify_order`, or
   `cancel_order` calls. Read-only broker APIs only (quotes, historical, holdings).
2. **No advisory language in any output.** Banned phrases: "buy", "sell",
   "guaranteed", "sure-shot", "tip", "recommendation". Use: "bullish watchlist
   candidate", "research interest", "score X/100", "needs confirmation".
3. **Every claim must cite its source.** News-based claims include the URL.
   Data-based claims include the timestamp and source feed. No floating
   assertions.
4. **Every report ends with a disclaimer block.** "For personal research and
   educational purposes only. Not investment advice. The operator has not paid
   for advice and Claude is not registered as an investment adviser or research
   analyst with SEBI."
5. **No NSE website scraping.** NSE Terms of Use prohibit systematic extraction.
   Permitted sources: broker APIs (Fyers/Dhan), `yfinance`, NewsAPI, Marketaux,
   FMP, Finnhub, public RSS feeds, exchange-published bhavcopies (downloadable),
   and SEBI/RBI press releases.
6. **No data exfiltration.** Vault contents, broker keys, and personal notes
   never leave the local machine in any tool call. No analytics, no telemetry.
7. **PII redaction in logs.** API keys, account numbers, and tokens never appear
   in logs, prints, or commit history. Use the `secrets/` directory and `.env`.
8. **SEBI personal-use boundary.** Anything in this repo is personal use as
   defined by SEBI's Feb 2025 circular: under 10 orders/sec, only the operator's
   own account. Do not add features that share signals with third parties.
9. **SCOPE LOCK** — When the operator gives a chunk-scoped task, do ONLY that
   chunk. Do not refactor unrelated files. Do not add features not requested.
   Do not "improve" adjacent systems while you're there. If you see something
   worth changing outside scope, write it to AGENTS.md as a follow-up note and
   STOP. The operator approves scope changes explicitly.

---

## 3. Stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | Type hints required; mypy in CI |
| API framework | FastAPI | Async by default |
| Agent orchestration | LangGraph | Not CrewAI. State, retries, schedules |
| Scheduler | APScheduler (in-process) | Celery only if we outgrow this |
| DB | PostgreSQL 16 + `pgvector` | One DB. No Qdrant until we have ≥ 6 months of news |
| Cache / queue | Redis 7 | Pub/sub for agent events, cache for prices |
| Knowledge layer | Obsidian vault (markdown + frontmatter) | The "brain" — see §6 |
| LLM serving | Ollama (local) | Models per task — see §5 |
| Sentiment (BERT) | FinBERT via `transformers` sidecar | Not on Ollama. Tiny FastAPI service |
| Embeddings | `nomic-embed-text` (default) / `bge-m3` (multilingual fallback) | Both via Ollama |
| Frontend | Next.js 14 + Tailwind + shadcn/ui | Server components default |
| Charts | Recharts (frontend) + matplotlib (reports) | |
| Containerization | Docker + docker-compose | Single-host deploy |
| Broker | Fyers API (primary) or Dhan (fallback) | Free, REST + WebSocket. Read-only scope |
| Alerts | Telegram bot + email (SMTP) | Never SMS, never public channels |

---

## 4. Indian-market specifics

### Market hours (IST)
- Pre-open: 09:00–09:15
- Regular: 09:15–15:30
- Post-close auctions: 15:40–16:00
- All times IST. Convert with `pytz.timezone("Asia/Kolkata")`. Never use UTC for
  scheduling display logic.

### Trading calendar
- Use the NSE holiday calendar (downloadable CSV from NSE) — load once a year,
  cache in Postgres.
- Saturday/Sunday closed. Some Saturdays open for muhurat or special sessions.
- Don't run intraday agents on holidays. The Universe Agent gates this.

### Tickers and symbols
- NSE symbol format: `RELIANCE`, `HDFCBANK`. yfinance suffix: `.NS` →
  `RELIANCE.NS`. BSE suffix: `.BO`. Maintain both in the `stocks` table.
- ISIN is the canonical key. Never join on symbol alone (collisions across
  exchanges, splits, name changes).
- Lot sizes change quarterly for F&O — refresh from exchange CSV monthly.

### Corporate actions
- Splits, bonuses, dividends — adjust historical price series. Use the broker's
  adjusted feed if available; otherwise apply the adjustment factor manually
  before any technical calculation. Wrong adjustment = fake breakouts.

### FII/DII data
- Source: NSE bhavcopies (downloadable, permitted) + SEBI provisional figures.
  These are end-of-day, not intraday. Don't pretend they're real-time.

### News sources (whitelist)
Tier A (high credibility): PIB, RBI, SEBI, exchange announcements, Reuters,
Bloomberg, Mint, BS, ET, Moneycontrol (corporate filings section).
Tier B: Moneycontrol news, ET Markets, BS Markets, CNBC-TV18.
Tier C (use with skepticism, weight 0.3×): Telegram channels, anonymous blogs,
unverified Twitter — only if cross-confirmed by Tier A/B.

### Backtesting integrity

- Backtest queries against `index_constituents` MUST filter by
  `effective_from <= trade_date < effective_to`.
- Never use today's universe to evaluate past periods — survivorship bias makes
  every strategy look better than it really was.
- Every backtest report must declare its as-of date and cite the constituent
  snapshot used.

---

## 5. Ollama model assignments

Pull these once: `ollama pull <name>`.

| Task | Model | Reason |
|---|---|---|
| Daily report writer | `qwen3.6:27b` (or `llama3.3:70b` if 48 GB+ VRAM) | Long-form structured prose |
| Meta-Auditor (CoT) | `deepseek-r1:32b` | Visible reasoning, catches weak claims |
| Tool-calling agents | `qwen3:8b` | Reliable JSON, low latency |
| Fast classifier | `llama3.2:3b` | News relevance, dedup, ticker matching |
| Embeddings | `nomic-embed-text` + `bge-m3` | Default + multilingual fallback |
| Vision (optional) | `qwen2.5vl:7b` | Chart / annual-report screenshots |

FinBERT runs in a separate sidecar (`services/finbert/`) on port 8765, called
over localhost. Ollama serves on default `:11434`.

Always specify the model explicitly in code — never rely on "default":

```python
OLLAMA_MODELS = {
    "report": "qwen3.6:27b",
    "auditor": "deepseek-r1:32b",
    "agent": "qwen3:8b",
    "classifier": "llama3.2:3b",
    "embed": "nomic-embed-text",
    "embed_multilingual": "bge-m3",
}
```

---

## 6. The Obsidian brain

The vault is the system's persistent knowledge layer. Path: `$VAULT_PATH`
(default `~/ResearchBrain`). Treat it as canonical for human-readable state;
treat Postgres as canonical for structured/transactional data. They are not
substitutes — they complement each other.

### Vault structure (do not deviate)

```
ResearchBrain/
├── 00_System/         project memory, prompt library, agent run logs
├── 01_Stocks/         one note per ticker, frontmatter is the contract
├── 02_Sectors/        one note per sector
├── 03_Macro/          USDINR, Crude, RBI, Fed, Yields
├── 04_Reports/Daily/  YYYY-MM-DD.md (auto-generated)
├── 05_Watchlists/     curated lists, one per file
├── 06_Decisions/      operator's trade journal (paper-trading)
├── 07_News/Inbox/     raw news drops, summarized into stock notes nightly
├── 08_Lessons/        post-mortems, model failure cases
└── 99_Templates/      Stock.md, DailyReport.md, Decision.md
```

### Frontmatter contract for `01_Stocks/<TICKER>.md`

```yaml
---
ticker: RELIANCE
isin: INE002A01018
exchange: NSE
sector: Energy
industry: Oil & Gas - Refining & Marketing
mcap_cr: 1850000
last_score: 78
score_breakdown: {tech: 82, fund: 76, news: 70, vol: 88, risk: 65}
signal: bullish-watch          # one of: bullish-watch | neutral | bearish-watch | avoid
confidence: 74                  # 0–100
last_updated: 2026-05-07T16:15+05:30
last_news_at: 2026-05-07T11:42+05:30
tags: [stock, energy, largecap]
---
```

This is a contract. The `Ranking Agent` writes `last_score`, `score_breakdown`,
`signal`, `confidence`. The `News Agent` updates `last_news_at`. The Universe
Agent writes the static fields. Never silently change the schema; if you must
add a field, add it to all existing notes in the same migration.

### How agents read/write the vault

Use `services/vault.py` — never touch markdown files directly from agent code.
All reads/writes go through this module so we have one place to enforce the
frontmatter contract, atomic writes, and Git-aware locking.

```python
from services.vault import vault

vault.read_stock("RELIANCE")              # → Stock note model
vault.update_stock_score("RELIANCE", ...) # atomic merge
vault.append_news("RELIANCE", news_item)  # appends to a date-stamped section
vault.write_daily_report(date, body)      # to 04_Reports/Daily/
```

### Sync

Use the Obsidian Git plugin. Auto-commit every 30 minutes. Push to a **private**
GitHub repo. Vault is in `.gitignore` for the main code repo — they are
separate repositories.

### 6.1 Vault as persistent memory for Claude Code

The vault at $VAULT_PATH (`C:/claude/vault/rahil claude`) is also
accessible to Claude Code via the filesystem MCP server. Claude Code
treats the vault as its persistent memory across sessions.

Operating rules for Claude Code's vault interactions:

1. AT THE START of every non-trivial session (anything beyond a one-line
   question), read the most recent lesson note in `08_Lessons/` and the
   most recent two daily agent logs in `00_System/AgentLogs/`. State
   what you read in 1-2 lines before proceeding.

2. AT THE END of any session that produced a chunk-level deliverable
   (a commit, a design decision, a debugging gotcha, a SCOPE LOCK
   refusal), write a lesson note to `08_Lessons/` named
   `<chunk-or-topic>-<YYYY-MM-DD>.md`. Use the structure of existing
   notes (frontmatter with date/phase/tags/status, body sections).

3. NEVER write to `04_Reports/` — those are agent-generated. Claude
   Code's writes go to `08_Lessons/`, `00_System/`, or
   `06_Decisions/` only.

4. When the operator asks "what did we learn about X" or "have we
   seen this before", grep the vault for relevant notes BEFORE
   answering from context.

5. The vault is canonical for prose and lessons. Postgres is canonical
   for structured data. If they disagree on a fact, the vault wins
   for narrative ("we decided X because Y") and the database wins
   for numbers ("Reliance closed at 2890.50").

6. Treat vault writes as commits — atomic, descriptive, complete.
   Don't write half a note and stop.

7. Vault structure (do not deviate):
   - 00_System/        — project memory, prompt library, agent logs
   - 01_Stocks/        — one note per ticker (agents fill in)
   - 02_Sectors/       — one note per sector
   - 03_Macro/         — USDINR, Crude, RBI, Fed, Yields
   - 04_Reports/       — agent-generated, do not write here
   - 05_Watchlists/    — operator + agent curated lists
   - 06_Decisions/     — design and trade decisions
   - 07_News/Inbox/    — raw news drops (agent-managed)
   - 08_Lessons/       — Claude Code writes here
   - 99_Templates/     — reusable note templates

Apply SCOPE LOCK to vault writes too. If you find yourself wanting
to write outside `08_Lessons/`, `06_Decisions/`, or `00_System/`,
stop and ask the operator first.

---

## 7. Repository layout

```
bharat-research-brain/
├── CLAUDE.md                      ← this file
├── README.md
├── docker-compose.yml
├── .env.example                   ← never commit .env
├── pyproject.toml
├── alembic/                       ← DB migrations
│
├── backend/
│   ├── main.py                    ← FastAPI entrypoint
│   ├── config.py                  ← pydantic-settings, reads .env
│   ├── db/
│   │   ├── models.py              ← SQLAlchemy models
│   │   ├── session.py
│   │   └── repositories/          ← data access, no business logic
│   ├── agents/
│   │   ├── base.py                ← BaseAgent: run(), schedule(), audit hook
│   │   ├── universe.py
│   │   ├── price.py
│   │   ├── technical.py
│   │   ├── fundamental.py
│   │   ├── news.py
│   │   ├── sentiment.py
│   │   ├── corporate_events.py
│   │   ├── sector.py
│   │   ├── macro.py
│   │   ├── flows.py               ← FII/DII
│   │   ├── risk.py
│   │   ├── ranking.py
│   │   ├── report.py
│   │   └── meta_auditor.py
│   ├── orchestration/
│   │   ├── graph.py               ← LangGraph definition
│   │   └── scheduler.py           ← APScheduler triggers
│   ├── data_sources/
│   │   ├── fyers.py               ← read-only client
│   │   ├── dhan.py                ← fallback
│   │   ├── yfinance_client.py
│   │   ├── newsapi.py
│   │   ├── marketaux.py
│   │   ├── fmp.py
│   │   └── nse_bhavcopy.py        ← downloadable files only, never scraping
│   ├── services/
│   │   ├── vault.py               ← Obsidian read/write
│   │   ├── ollama.py              ← LLM client wrapper
│   │   ├── finbert.py             ← sidecar HTTP client
│   │   ├── alerts.py              ← Telegram + email
│   │   └── citations.py           ← enforces every claim has a source
│   ├── api/                       ← FastAPI routers
│   └── tests/
│
├── services/finbert/              ← separate FinBERT sidecar (FastAPI + transformers)
│
├── frontend/                      ← Next.js dashboard
│
└── scripts/
    ├── seed_universe.py           ← initial Nifty 500 ingest
    ├── refresh_lot_sizes.py
    └── vault_migrate.py           ← schema migrations for stock notes
```

---

## 8. Coding conventions

- **Async-first.** All I/O is `async`. Sync code only inside CPU-bound functions
  wrapped in `asyncio.to_thread`.
- **Type hints required.** `from __future__ import annotations` at the top of
  every file. `mypy --strict` on `backend/`.
- **Pydantic v2** for all data contracts crossing module boundaries.
- **Logging.** `structlog`. Every log line includes `agent`, `run_id`, and
  `correlation_id`. No `print()`.
- **Errors.** Define a `BharatError` base + specific subclasses (`DataSourceError`,
  `VaultIntegrityError`, `LLMError`). Never `except Exception: pass`.
- **Retries.** Use `tenacity`. Exponential backoff on every external API.
  Default: 3 retries, max wait 30s, retry only on idempotent operations.
- **Time.** Always timezone-aware. `datetime.now(IST)` not `datetime.now()`.
  Persist as UTC, display as IST.
- **Money.** Never `float`. Use `Decimal`. Round-half-even.
- **Tests.** `pytest` + `pytest-asyncio`. Every agent has at least one happy-path
  test with mocked external calls. Use `respx` for HTTP mocks.
- **Docstrings.** Public functions only, Google style. Prefer clear names over
  long docstrings.
- **Imports.** stdlib → third-party → local, separated by blank line. `ruff`
  enforces.
- **No magic numbers.** Constants in `backend/constants.py`.

---

## 9. Agent contract

Every agent inherits from `BaseAgent` and implements:

```python
class BaseAgent(ABC):
    name: str
    schedule: str | None         # cron expression or None for event-driven

    async def run(self, ctx: RunContext) -> AgentOutput: ...
    async def health(self) -> HealthStatus: ...
```

`AgentOutput` always includes:
- `claims: list[Claim]` — each claim has `text`, `evidence` (URL or data row),
  `confidence` (0–1)
- `metrics: dict[str, float]`
- `vault_writes: list[VaultWrite]` — what the agent wrote to Obsidian
- `errors: list[AgentError]`

The Meta-Auditor receives this output and rejects claims with no evidence,
contradictory confidence, or stale data (>1 hour old during market hours,
>1 day off-hours).

---

## 10. Build phases (follow in order)

**Do not skip phases.** Each phase ends with a working, demoable system.

1. **Phase 0 — Foundations (week 1):** Repo scaffolding, Postgres + Redis
   docker-compose, Fyers/Dhan auth flow, basic FastAPI health endpoint, Obsidian
   vault initialized with templates. Outcome: `docker compose up` runs clean.
2. **Phase 1 — Data spine (weeks 2–3):** Universe Agent (Nifty 500 + sector
   mapping), Price Agent (Fyers WebSocket → Postgres), `vault.py` write path,
   end-of-day price snapshot to stock notes. No LLMs yet.
3. **Phase 2 — First report (weeks 4–5):** News Agent (NewsAPI + Marketaux +
   2 RSS), FinBERT sidecar, simplest possible Report Agent that produces
   `04_Reports/Daily/YYYY-MM-DD.md`. Telegram delivery. One agent end-to-end.
4. **Phase 3 — Analytics (weeks 6–7):** Technical Agent (RSI/MACD/SMA/VWAP
   from price history), Fundamental Agent (FMP or screener.in if allowed),
   Sector Agent, Risk Agent. Ranking Agent merges scores. Update stock notes.
5. **Phase 4 — Intelligence (weeks 8–9):** Macro Agent, FII/DII Agent (from
   bhavcopies), Corporate Events Agent, Meta-Auditor. LangGraph orchestration
   replaces ad-hoc scheduling. Dashboard MVP.
6. **Phase 5 — Backtesting (weeks 10–11):** Historical replay harness. Walk-
   forward signal evaluation. PnL simulator on paper trades. **Until signals
   beat Nifty buy-and-hold on a risk-adjusted basis, no further features.**
7. **Phase 6 — Polish (week 12+):** Dashboard, alert hygiene (rate limits,
   priority levels), vault search UI, lessons-learned automation.

---

## 11. Things you must always do

- **Cite sources.** Every news-based statement gets a URL. Every data point gets
  a timestamp and feed name. The Meta-Auditor enforces this — make its job easy.
- **Treat data as suspect.** Cross-check at least two sources for any claim
  that drives a signal. Stale data is worse than missing data.
- **Use timezone-aware datetimes.** IST for display, UTC for storage.
- **Use Decimal for money.** Floats lose paise. Paise compound.
- **Write to the vault through `services/vault.py`.** Never raw file writes.
- **Log structured events.** Future-you needs to debug a failure at 14:47 IST
  on a Friday.
- **Fail loud on data source errors during market hours.** Silent fallback to
  stale prices is the worst possible outcome.

## 12. Things you must never do

- **Never write order-placement code.** If the user asks, refuse and refer them
  to this CLAUDE.md, §2 rule 1.
- **Never use advisory language.** §2 rule 2.
- **Never scrape `nseindia.com`** or any page that requires automating a browser
  to bypass rate limits. Use bhavcopies and broker APIs.
- **Never store API keys in code or commit them.** Use `.env` and the
  `secrets/` directory (gitignored).
- **Never silently retry forever.** Every retry policy has a max.
- **Never use `eval()`, `exec()`, or `pickle.loads()` on external input.**
- **Never let an LLM call out to an unfamiliar URL.** The fetch tools have an
  allow-list.
- **Never fabricate.** If a data source is down, say so in the report. Do not
  fill gaps with "estimated" numbers.

---

## 13. Definition of done (per feature)

A feature is done when:

1. It has tests with at least one mocked external call.
2. It logs structured events at start, success, and failure.
3. It updates the relevant Postgres tables and vault notes.
4. It produces output that passes the Meta-Auditor (claims have evidence).
5. The README's "Architecture" section is updated if this changed it.
6. Operator can demo it from a fresh `docker compose up` in under 5 minutes.

---

## 14. Environment variables (reference)

See `.env.example` for the full list. Critical ones:

```
# Broker (read-only scope)
FYERS_APP_ID=
FYERS_SECRET=
FYERS_REDIRECT_URI=
FYERS_ACCESS_TOKEN=

# News
NEWSAPI_KEY=
MARKETAUX_KEY=
FMP_KEY=

# Infra
POSTGRES_URL=postgresql+asyncpg://...
REDIS_URL=redis://localhost:6379/0
OLLAMA_HOST=http://localhost:11434
FINBERT_HOST=http://localhost:8765

# Vault
VAULT_PATH=/Users/you/ResearchBrain

# Alerts
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
SMTP_HOST=
SMTP_USER=
SMTP_PASS=

# Timezone
TZ=Asia/Kolkata
```

---

## 15. When in doubt

- If a task seems to violate §2 (hard rules), refuse and ask the operator.
- If the operator asks for "auto-trading", "live signals to subscribers", or
  similar, refuse and refer to §2 rules 1 and 2 and the SEBI personal-use
  boundary in rule 8.
- If a data source is misbehaving, prefer "no signal" over "guess".
- If the vault and Postgres disagree, **the vault wins for prose and the database
  wins for numbers.** Reconcile via a migration, not a hack.
- If something is unclear, search the codebase, then the vault's
  `08_Lessons/` directory, then ask.

---

*End of CLAUDE.md. Last updated: 2026-05-07.*

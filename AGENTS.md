# AGENTS.md — Indian Stock Research Intelligence System

> This file is read by Codex at the start of every session. It is the single
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
   for advice and Codex is not registered as an investment adviser or research
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
| LLM | DeepSeek API (`deepseek-chat`) | Cloud API; Ollama retired — see §5 |
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

---

## 5. LLM: DeepSeek API (`deepseek-chat`)

The system's LLM is the **DeepSeek API** (model `deepseek-chat`). **Ollama has been
retired** — removed from `docker-compose.yml` on 2026-05-28. Do NOT call Ollama
(`http://…:11434`), run `ollama pull`, or assume a local model server exists; there
is none. Set `DEEPSEEK_API_KEY` in `.env`.

| Task | Model | Reason |
|---|---|---|
| Daily report writer | `deepseek-chat` | Long-form structured prose |
| Meta-Auditor (CoT) | `deepseek-chat` (or `deepseek-reasoner` for visible CoT) | Catches weak claims |
| Tool-calling agents | `deepseek-chat` | Reliable JSON, low latency |
| Fast classifier | `deepseek-chat` | News relevance, dedup, ticker matching |

Always specify the model explicitly in code — never rely on a "default".

FinBERT is a separate sentiment sidecar (`services/finbert/`, port 8765) — it was
never an Ollama dependency. NOTE: the sidecar is **not yet implemented** (the
directory holds only `.gitkeep`), so `sentiment` is non-functional until it is built.

> Migration follow-up (open): embeddings (was `nomic-embed-text` / `bge-m3` via
> Ollama) and optional vision (`qwen2.5vl:7b`) need a non-Ollama provider — DeepSeek's
> API does not serve embeddings. Decide a replacement before any embedding/vector
> feature runs.

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

---

## 7. Repository layout

```
bharat-research-brain/
├── AGENTS.md                      ← this file
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
  to this AGENTS.md, §2 rule 1.
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

## 16. Follow-ups (out-of-scope flags surfaced during chunk work)

Operator decides whether to action each. Format: date · chunk · description · status.

- **2026-05-07 · Phase 1 Chunk 1.1 commit 7 · Dockerfile does not copy `alembic/` or `alembic.ini` into the backend image.** Required for `docker compose exec backend alembic ...` (used in commit 8 of the implementation prompt). Three options: patch Dockerfile, bind-mount via docker-compose, or run alembic from host. Recommendation: patch Dockerfile. Status: awaiting operator authorization.
- **2026-05-07 · Phase 0 commit 1 · `AGENTS.md` got tracked by `git add .`.** Operator stated "leave it alone" but did not specify "untrack". One-line `git rm --cached AGENTS.md` if untrack desired. Status: open.
- **2026-05-07 · Phase 1 Chunk 1.1 commit 7 · `pyproject.toml` gained `alembic>=1.13` and `psycopg[binary]>=3.2`.** Implicit in Alembic configuration (the env.py adapter swap to `postgresql+psycopg` requires psycopg). Surfacing for record; operator-acknowledged via the commit-7 authorization. Status: applied.
- **2026-05-07 · Phase 1 Chunk 1.2 commit 10 · `backend/cli.py` `version` shows wrong schema_version row when ties exist.** When multiple `schema_version` rows share the same `applied_at` second (e.g., 0002 + 0003 applied in one `alembic upgrade head`), `ORDER BY applied_at DESC LIMIT 1` picks arbitrarily — observed: showed `0002_seed_indices` instead of `0003_seed_trading_calendar`. Fix: change ORDER BY to `applied_at DESC, version_label DESC` for deterministic tie-break. Status: FIXED 2026-05-24 — `backend/cli.py` now orders by `applied_at DESC, version_label DESC`.
- **2026-05-08 · Phase 1 Chunk 1.2 commit 11 · NIFTYFINSERVICE filename DEFERRED.** First-run verification revealed `ind_niftyfinancialserviceslist.csv` returns the niftyindices.com soft-404 HTML page (HTTP 200, body = `<title>Error 404</title>`). Map entry now `_DEFERRED_FILENAME` sentinel; client raises `DataSourceError(reason_code='deferred_filename')` on access without making any HTTP call. Operator action: verify the correct filename via browser at https://www.niftyindices.com/indices/equity/sectoral-indices/nifty-financial-services and paste back for a commit 11.5 update. Status: deferred, blocking commit 13 if NIFTYFINSERVICE included in the universe.
- **2026-05-08 · Phase 1 Chunk 1.2 commit 11 · niftyindices.com soft-404 pattern.** Server returns HTTP 200 with HTML body containing "Error 404" when a path is invalid. Detection now in `NiftyIndicesClient._raise_if_html` via prefix-sniff for `<!doctype` / `<html` / `<?xml`. Pattern likely applies to other Indian-data-source servers — reuse the helper or replicate the sniff when adding new clients. Status: applied (in commit 11).
- **2026-05-08 · Phase 1 Chunk 1.2 commit 11 · OpenAlgo cross-check deferred to Phase 1.5.** `backend/data_sources/openalgo.py` is a stub returning empty list with `is_stub=True`. Real implementation requires OpenAlgo auth setup. Universe Agent tolerates empty stub returns as "tertiary source unavailable". Status: deferred.
- **2026-05-25 · Phase 1 Chunk 1.3 commit B · `prices.bulk_insert` signature extended beyond the build spec.** Spec said `bulk_insert(rows) -> int`; implemented as `bulk_insert(session, rows, *, ingestion_run_id, source='nse_bhavcopy')` because `prices_eod.ingestion_run_id` is `NOT NULL` (FK to `data_ingestion_runs.id`). The Price Agent resolves the run pk inside `_execute` via `SELECT id FROM data_ingestion_runs WHERE run_id = ctx.run_id` (base.run commits the open row before calling `_execute`, so it is visible). No schema change. Status: applied, surfaced for record.
- **2026-05-25 · Phase 1 Chunk 1.3 · NSE bhavcopy column/unit bug found during first real backfill.** UDiFF new format uses `TtlTradgVol`/`TtlTrfVal`/`TtlNbOfTxsExctd` (not `TtlTrdQnty`/`TtlTrdVal`/`TtlNbOfTxnsExctd` per the build spec). Delivery columns are absent from UDiFF — they live in a separate file. Both formats: traded value is in RUPEES, not crores or lakhs. `turnover_inr` = raw rupees value; `value_inr_cr` = raw / 1e7. The spec's "new=crores"/"old=lakhs÷100" was wrong; live data is ground truth. The wrong `value_inr_cr × 1e7` had overflowed `turnover_inr` `Numeric(20,4)` for large-caps, crashing the first backfill (nothing written — atomic rollback). Status: FIXED 2026-05-25 in `nse_bhavcopy.py` parsers + tests.
- **2026-05-25 · Phase 1 Chunk 1.3 commit B · `prices_eod.turnover_inr` stored in RUPEES, not crores.** The bhavcopy parser exposes `BhavRow.value_inr_cr` in crores (new format as-is; old format = `TOTTRDVAL` lakhs ÷ 100). The DB column is named `turnover_inr`, so `bulk_insert` multiplies by 1e7 (crores → rupees) to match the column's INR semantics. Downstream readers must treat `turnover_inr` as rupees. Status: applied, surfaced for record.

---

## Image strategy: dev tools baked into runtime image (2026-05-08)

For personal-research phase, the backend container image installs
the [dev] optional dependency group alongside main deps. Ruff,
mypy, pytest, pytest-asyncio, and respx live in the same image
the agents run in. ~50MB bloat is irrelevant at this scale.

When we eventually have a production deployment (Phase 6+), revisit
via multi-stage build with separate `runtime` and `dev` targets.
Don't pre-optimize before then.

Pattern matches commit d69500c (alembic + psycopg also baked in).

---

## Migration patch / image rebuild gotcha (2026-05-07)

When hand-patching an autogenerated alembic migration:
- Patches applied via host-side editor only modify the host file.
- The container's mutable fs and the docker image still hold the
  unpatched version.
- `alembic upgrade head` inside the container runs the IMAGE's copy
  of the migration, NOT the host's.
- Always: rebuild backend image (`docker compose build backend
  --no-cache`) after any migration patch, BEFORE upgrade.
- Verify by grep'ing for patch markers inside the container before
  running upgrade.

---

*End of AGENTS.md. Last updated: 2026-05-07.*

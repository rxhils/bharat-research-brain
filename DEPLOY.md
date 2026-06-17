# DEPLOY.md — Forward F+ paper-trading engine (always-on)

Runs the **frozen F+ engine** (commit `57e72d5`) forward as a paper portfolio
(₹10,00,000), one nightly job, against a hosted Postgres. This is a **paper, forward,
out-of-sample** track record — it starts at inception and only grows forward, never
backfilled.

> Prereq: hosted Postgres provisioned + schema/data loaded — see **HOSTED_DB.md** first.

---

## 0. Cloud data strategy (free-tier safe — keep history local)

The local DB is **545 MB** (over Supabase's 500 MB free tier), but that is **96%
backtest history**: `prices_eod` (276 MB) + the full `prices_eod_adjusted`
(247 MB, 1.06M rows back to 2015). **The forward system does not need any of that.**

The 24/7 forward system needs only ~**50–80 MB**:
- the **last ~400 trading days** of `prices_eod_adjusted` (≈195k rows ≈ 45 MB) for scoring
- `stocks`, `benchmark_index`, `{fundamental,macro,sector}_signals_historical`,
  `stock_rankings` (composite inputs)
- support: `trading_calendar`, `index_constituents`, `stock_identifiers`
- the F+ portfolio state: `paper_account/position/equity_curve/event_log` (~0.14 MB)

**Plan: keep the 1.06M historical rows LOCAL (backtest is done), push only the
forward slice to Supabase.** No need for Supabase Pro.

```bash
# A. Create the Supabase project, grab its connection string. Then create the schema:
FORWARD_TARGET_URL='postgresql://USER:PASS@HOST:5432/postgres?sslmode=require'
alembic upgrade head        # run with POSTGRES_URL pointed at Supabase (the +asyncpg form)

# B. Preview the forward footprint (no target needed — confirms it fits 500 MB):
python -m scripts.migrate_forward_to_supabase --dry-run

# C. Migrate ONLY the forward data (idempotent, ON CONFLICT DO NOTHING, re-runnable):
FORWARD_SOURCE_URL='postgresql://bharat:PASS@localhost:5432/bharat' \
FORWARD_TARGET_URL="$FORWARD_TARGET_URL" \
python -m scripts.migrate_forward_to_supabase
```

After this, the VM/worker and Vercel both point `POSTGRES_URL`/`DATABASE_URL` at
Supabase, and the daily ingest keeps the recent-price window fresh going forward.

---

## 1. Resource sizing (measure before you pick a VM)

| Workload | What it needs | RAM |
|---|---|---|
| **Paper engine + mechanical composite** (today's setup) | Python + pandas + asyncpg + yfinance EOD; LLM = **DeepSeek API** (cloud, no local model) | **< 1 GB** → smallest VM is fine |
| **+ Agentic pipeline once keys exist** | adds FinBERT sentiment — `transformers`/`torch` loaded **in-process** in the backend image (AGENTS.md §5), lazy-loaded on first sentiment run | torch resident ≈ **1.5–2 GB** → size the VM at **4 GB** |

**Today we run the mechanical-composite engine only** (News/FII/Fundamental agents
are dormant — keys empty), so a **1–2 GB VM (or a Railway scheduled job)** is enough.
NOTE: I did not boot FinBERT this session, so the 1.5–2 GB figure is the typical
`torch`+FinBERT resident set, not a measured number on this host — measure with
`docker stats` the first time you enable the sentiment agent before committing to VM size.

DeepSeek is a **cloud API** (`DEEPSEEK_API_KEY`) — no GPU, no local model server
(Ollama was retired, AGENTS.md §5).

---

## 2. Option A — small Linux VM (Hetzner CX22 / DigitalOcean basic, ~2 GB)

```bash
# on the VM (Ubuntu 24.04)
sudo apt update && sudo apt install -y git python3.11 python3.11-venv postgresql-client
git clone <your-private-repo> bharat && cd bharat
python3.11 -m venv .venv && . .venv/bin/activate
pip install -e .            # or: pip install -r requirements + the [dev] group

# env — NEVER commit this file
cat > .env <<'EOF'
POSTGRES_URL=postgresql+asyncpg://<user>:<pass>@<supabase-host>:5432/postgres?ssl=require
DEEPSEEK_API_KEY=sk-...        # rotate the one printed in chat
TZ=Asia/Kolkata
# Optional but recommended — nightly_run pings here on success/failure:
TELEGRAM_BOT_TOKEN=            # from @BotFather
TELEGRAM_CHAT_ID=             # your chat/channel id
# (leave NEWSAPI_KEY / FMP_KEY / FYERS_ACCESS_TOKEN empty until you enable agents)
EOF

# one-time: apply migrations to the hosted DB (idempotent)
alembic upgrade head

# verify connectivity + data
python -m scripts.test_hosted_db

# GO LIVE (once, after a clean dry-run) — sets inception at the latest EOD close
python -m scripts.paper_inception              # dry-run preview first
python -m scripts.paper_inception --commit     # inception_date = today's EOD
```

### cron (daily, after NSE close — one entrypoint does everything)
NSE closes 15:30 IST; today's EOD bar is published a few hours later, so run at 19:00 IST.
Use the single **`scripts.run_daily`** entrypoint — it does, in strict order:
ingest_eod (fetch today's real EOD) → **freshness gate** (abort if prices didn't advance
to the expected last NSE trading day — never run F+ on stale data) → nightly_run (F+) →
one `DAILY RUN OK …` log line.
```cron
# m h  dom mon dow   command   (server TZ = Asia/Kolkata)
0 19 * * 1-5  cd /home/ubuntu/bharat && . .venv/bin/activate && python -m scripts.run_daily >> /var/log/paper_daily.log 2>&1
```
The weekly (5-trading-day) and quarterly (63-trading-day) logic **self-triggers inside
`nightly_run.py`** by trading-day count since inception — no extra cron entries. The
freshness gate exits non-zero on stale data, so a failed run is visible in the log and
F+ is NOT advanced on a missing day (the gap is logged for the next run to surface).

## 2. Option B — Railway scheduled job
- Deploy the repo as a Railway service; set the env vars above in the Railway dashboard.
- Add a **Cron schedule** `0 19 * * 1-5` (set service TZ to Asia/Kolkata) running
  `python -m scripts.nightly_run`.
- Use Railway's managed Postgres **or** point `POSTGRES_URL` at Neon (one DB for both
  the job and any future Vercel dashboard).

---

## 3. Verify a successful nightly run
1. **Exit code 0** and a log line `nightly.done as_of=YYYY-MM-DD`.
2. **A new row in `paper_equity_curve`** for the latest trading date:
   ```sql
   SELECT trade_date, total_equity, cash_value, exposure_level, drawdown_pct
   FROM paper_equity_curve ORDER BY trade_date DESC LIMIT 3;
   ```
3. **Event log** shows the day's actions:
   ```sql
   SELECT trade_date, event_type, detail FROM paper_event_log
   ORDER BY id DESC LIMIT 10;
   ```
4. On weekly/quarterly days, expect an `exposure_change` / `rebalance` event.
A run that produces no new `paper_equity_curve` row = the EOD price ingest didn't land;
fix ingest before trusting the record (a gappy record is compromised — re-incept if so).

---

## 4. Honesty / operating notes
- The record is **PAPER, forward, starts at inception** — not backfilled, label it so.
- It is **not meaningful for ~6–12 months** and won't see a real crash until one happens.
- F+ is the validated **risk-managed** engine (index-like return, ~half the drawdown).
  Today the forward test measures **F+ itself** on the mechanical composite. It tests
  **whether the agents add value** only after you add `NEWSAPI_KEY`/`FMP_KEY`/
  `FYERS_ACCESS_TOKEN` and switch the score source to `stock_rankings`.
- Cash earns **0%** in the ledger (conservative; real Indian cash ≈ 6%, so the record
  is shown slightly worse than reality).

---

## 5. Frontend dashboard (Vercel) + the full 24/7 stack

You chose **cloud**. One Neon DB is the single source of truth; the worker writes it,
Vercel reads it.

```
   Render/Railway worker ──(writes)──► Neon Postgres ◄──(reads)── Vercel (maven-dashboard)
   ingest_eod + nightly_run            paper_* tables             real Portfolio + Brain
```

### Deploy the dashboard (Vercel)
1. New Project → **root directory `maven-dashboard`** (it's a separate Next.js app).
2. Env var **`DATABASE_URL`** = the Supabase **pooled** URL, ideally a **read-only**
   role (the dashboard only SELECTs — create a `readonly` Postgres role with `GRANT
   SELECT` and use its credentials so a leaked Vercel env var can't write). NOTE: the
   dashboard uses the `pg` driver, so use the plain `postgresql://...` form — **not**
   `+asyncpg` (that's the backend worker's form). SSL is auto-enabled for any
   non-localhost host.
3. Deploy. Portfolio + Brain now render the real Neon record. Locally the same is driven
   by `maven-dashboard/.env.local` (gitignored) → local Docker Postgres.

### Daily fresh-data chain (built)
`scripts/ingest_eod.py` (yfinance EOD for the active universe, append-only via
`ON CONFLICT DO NOTHING`, no NSE scraping) + `scripts/run_daily.py` (ingest →
freshness gate → F+) are in place. Point the cron at `scripts.run_daily` (above).
The freshness gate guarantees the cloud portfolio only advances on **genuinely fresh
real prices** — if the latest price date hasn't reached the expected last NSE session
(e.g. yfinance hasn't published yet, or a day was missed), it **aborts** with a clear
error and does NOT produce trades on stale data.

### Live Agent board + Telegram (now wired)
`scripts/nightly_run.py` already writes an `agent_run_log` heartbeat
(`running`→`done`/`error`, agent `NightlyRun`) via `backend/agents/run_log.py::heartbeat()`,
so the Brain "Agents" board lights up the moment a run happens. It also sends a Telegram
ping on success/failure when `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` are set, e.g.
`✅ Run complete, latest 2026-06-17, F+ holds 25, exposure 1.0, equity Rs …` or
`❌ Nightly run FAILED: <error>`. Both are best-effort — neither can alter or block the
F+ decisions.

### Before you deploy
- **Rotate** any API keys pasted into chat (NewsAPI / FMP / indianapi / DeepSeek).
- `npm i next@14.2` in `maven-dashboard` to clear the pinned-14.2.15 security advisory.

### Is it actually running? (cloud checklist)
- `SELECT max(trade_date) FROM prices_eod_adjusted;` advances each weekday → ingest works.
- `SELECT count(*) FROM paper_equity_curve;` grows by one per trading day → nightly_run works.
- Vercel portfolio value changes after each nightly run. If it never moves, the cron or the
  ingest isn't running.

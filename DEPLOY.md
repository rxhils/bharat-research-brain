# DEPLOY.md — Forward F+ paper-trading engine (always-on)

Runs the **frozen F+ engine** (commit `57e72d5`) forward as a paper portfolio
(₹10,00,000), one nightly job, against a hosted Postgres. This is a **paper, forward,
out-of-sample** track record — it starts at inception and only grows forward, never
backfilled.

> Prereq: hosted Postgres provisioned + schema/data loaded — see **HOSTED_DB.md** first.

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
POSTGRES_URL=postgresql+asyncpg://<user>:<pass>@<neon-host>/<db>?ssl=require
DEEPSEEK_API_KEY=sk-...        # rotate the one printed in chat
TZ=Asia/Kolkata
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

### cron (daily, after NSE close + your EOD price ingest)
NSE closes 15:30 IST; run after your price-ingest job finishes (say 19:00 IST):
```cron
# m h  dom mon dow   command   (server TZ = Asia/Kolkata)
0 19 * * 1-5  cd /home/ubuntu/bharat && . .venv/bin/activate && python -m scripts.nightly_run >> /var/log/paper_nightly.log 2>&1
```
The weekly (5-trading-day) and quarterly (63-trading-day) logic **self-triggers inside
`nightly_run.py`** by trading-day count since inception — no extra cron entries.
Price ingest (yfinance EOD) must run **before** this; chain it in the same cron line or
an earlier entry.

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

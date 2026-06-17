# DEPLOY.md — Bharat Brain forward worker on a VPS (Ubuntu 24.04)

Runs the **FROZEN F+ paper engine** (commit `57e72d5`) 24/7 via cron, writing to
**Supabase**. **Deployment only — F+ logic is untouched.** You are `root`, SSH'd into the
Hostinger VPS (2 vCPU / 8 GB, Mumbai). Copy-paste each block in order.

**Nightly job** = `scripts.run_daily`:
`ingest today's EOD prices → assert freshness (ABORT on stale, never trade on old data) →
F+ mark / exposure / rebalance → one verifiable log line`.

**Architecture:** VPS (cron worker) → writes → **Supabase Postgres** ← reads ← Vercel (dashboard).

> The Supabase DB already has the schema + 507 stocks + benchmark + the F+ paper account
> (incepted 2026-04-15, migrated). **Do NOT run `paper_inception` on the VPS** — the worker
> only continues the record forward.

---

## 0. What reads what (so you fill the right env var)

The **only** env var the nightly worker needs is **`POSTGRES_URL`** (read by `ingest_eod`,
`nightly_run`, `run_daily` via the backend config → `SessionLocal`). Use the **asyncpg**
form with **`?ssl=require`** (NOT `sslmode` — asyncpg rejects it).

| Var | Read by | Needed on VPS? |
|---|---|---|
| `POSTGRES_URL` | ingest_eod / nightly_run / run_daily | ✅ **YES** |
| `DATABASE_URL` | Maven dashboard (`pg`) only | ❌ no (set it on Vercel) |
| `NEWSAPI_KEY` / `DEEPSEEK_API_KEY` / `INDIANAPI_KEY` | dormant agentic layer only | ❌ no (config ignores them) |

---

## 1. System setup
```bash
apt update && apt -y upgrade
apt -y install python3 python3-venv python3-pip git
python3 --version          # Ubuntu 24.04 -> 3.12, satisfies the project's "3.11+"
```
psycopg/asyncpg ship binary wheels, so no build deps are needed. (Only if a source build
is ever forced: `apt -y install build-essential libpq-dev`.)

**venv over Docker** on a 2-core box: a cron worker in a venv is lighter (no daemon, no
image builds), logs are immediate, and there's nothing running between nightly fires.

---

## 2. Get the code
```bash
cd /root
git clone https://github.com/rxhils/bharat-research-brain.git
cd bharat-research-brain
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -e .           # installs the project + deps (yfinance, asyncpg, sqlalchemy, ...)
```

### Create `.env` — TEMPLATE (fill in your NEW password; this file is gitignored)
```bash
cat > /root/bharat-research-brain/.env <<'EOF'
# REQUIRED - the ONLY var the nightly worker reads (backend config -> SessionLocal).
# asyncpg form + ?ssl=require  (Supabase Session Pooler, IPv4, Mumbai).
POSTGRES_URL=postgresql+asyncpg://postgres.jsztodaxbchuoyjwpblq:NEW_PASSWORD_HERE@aws-1-ap-south-1.pooler.supabase.com:5432/postgres?ssl=require

TZ=Asia/Kolkata

# OPTIONAL - NOT read by the F+ nightly chain (leave blank here):
#   DATABASE_URL   -> dashboard only (set on Vercel, plain postgresql:// no +asyncpg)
#   NEWSAPI_KEY / DEEPSEEK_API_KEY / INDIANAPI_KEY -> dormant agentic layer only
EOF
chmod 600 /root/bharat-research-brain/.env
```
- Replace `NEW_PASSWORD_HERE` with your rotated password.
- If the password has special chars, URL-encode them: `@`->`%40`, `:`->`%3A`, `/`->`%2F`, `#`->`%23`.

---

## 3. Connectivity tests (from the VPS)
```bash
cd /root/bharat-research-brain && . .venv/bin/activate

# (A) Supabase reachable + the worker's real DB path (SQLAlchemy+asyncpg):
python - <<'PY'
import asyncio
from backend.db.session import SessionLocal
from sqlalchemy import text
async def m():
    async with SessionLocal() as s:
        v = (await s.execute(text("select version()"))).scalar_one()
        n = (await s.execute(text("select count(*) from stocks"))).scalar_one()
        print("SUPABASE OK:", v[:40], "| stocks:", n)
asyncio.run(m())
PY
```
**PASS** = `SUPABASE OK: PostgreSQL 17.x ... | stocks: 507`.
If `failed to resolve host` -> you used the IPv6 direct host; keep the
`aws-1-ap-south-1.pooler.supabase.com` pooler host. If `password authentication failed` ->
re-check the rotated password / URL-encoding.

```bash
# (B) yfinance / NSE EOD fetch works from this datacenter (not geo-blocked):
python - <<'PY'
import yfinance as yf
df = yf.Ticker("RELIANCE.NS").history(period="5d", auto_adjust=False)
print("YFINANCE OK rows:", len(df),
      "| last close:", round(float(df['Close'].iloc[-1]), 2) if len(df) else "NONE")
PY
```
**PASS** = `YFINANCE OK rows: 5 ...`. If `rows: 0`, yfinance is blocked from this IP (rare on
a Mumbai DC) — tell me and we'll switch the price source.

---

## 4. Test the nightly chain manually (the real test)
```bash
cd /root/bharat-research-brain && . .venv/bin/activate

# BEFORE - note the latest price date + curve length:
python - <<'PY'
import asyncio
from backend.db.session import SessionLocal
from sqlalchemy import text
async def m():
    async with SessionLocal() as s:
        print("latest price BEFORE:", (await s.execute(text("select max(trade_date) from prices_eod_adjusted"))).scalar_one())
        print("curve rows  BEFORE :", (await s.execute(text("select count(*) from paper_equity_curve"))).scalar_one())
asyncio.run(m())
PY

# RUN the full chained job (ingest -> freshness assert -> F+):
python -m scripts.run_daily ; echo "EXIT=$?"

# AFTER:
python - <<'PY'
import asyncio
from backend.db.session import SessionLocal
from sqlalchemy import text
async def m():
    async with SessionLocal() as s:
        print("latest price AFTER:", (await s.execute(text("select max(trade_date) from prices_eod_adjusted"))).scalar_one())
        print("curve rows  AFTER :", (await s.execute(text("select count(*) from paper_equity_curve"))).scalar_one())
asyncio.run(m())
PY
```
**PASS criteria:**
- `STEP 1 ingest_eod ...` fetches the latest EOD; **latest price date advances** to the last NSE session.
- `FRESHNESS OK: prices as of <date> == expected last NSE session <date>`.
- `STEP 3 nightly_run (F+)...` then `DAILY RUN OK - ... equity Rs ...`.
- **curve rows AFTER > BEFORE** (a new `paper_equity_curve` row) — unless the market was
  closed today, in which case it's a correct no-op.
- `EXIT=0`.

> The bare `ingest_eod && nightly_run` you mentioned also works, but **`run_daily` is
> strictly safer** — it inserts the freshness gate between them (step 5). Use `run_daily`.

---

## 5. Freshness guard (already built — verify it)
`run_daily` STEP 2 asserts `max(price_date) == expected last NSE trading day` (from the
`trading_calendar`). If prices did **not** advance (yfinance returned nothing, or the EOD
bar isn't published yet), it **ABORTS with `EXIT=1` and F+ never runs** — so it can never
produce fake trades on stale data. It also logs any missed-day gaps in the record.

Verify the gate (run without re-ingesting):
```bash
python -m scripts.run_daily --no-ingest ; echo "EXIT=$?"
```
- Stored data already at the expected session -> `FRESHNESS OK` + an F+ no-op (no duplicate
  trade). `EXIT=0`.
- Stored data behind the expected session -> `FRESHNESS ABORT: prices are STALE ... F+ NOT
  run on stale data`. `EXIT=1`.

Both outcomes are correct: **each trading day is marked exactly once; stale data never marks.**

---

## 6. Cron (daily, after NSE close, Asia/Kolkata)
```bash
# 1) set the VPS clock to IST so cron + logs are in market time:
timedatectl set-timezone Asia/Kolkata
timedatectl | grep "Time zone"

# 2) logs dir:
mkdir -p /root/bharat-research-brain/logs

# 3) install the crontab (19:00 IST, Mon-Fri - EOD is published well before 19:00):
( crontab -l 2>/dev/null; \
  echo 'CRON_TZ=Asia/Kolkata'; \
  echo '0 19 * * 1-5 cd /root/bharat-research-brain && /root/bharat-research-brain/.venv/bin/python -m scripts.run_daily >> /root/bharat-research-brain/logs/nightly.log 2>&1' \
) | crontab -

crontab -l        # verify both lines are present
```
- `CRON_TZ=Asia/Kolkata` makes `0 19` fire at **19:00 IST**.
- `run_daily` self-skips weekends/holidays (freshness abort / no-op), so `1-5` is safe.
- **Log file:** `/root/bharat-research-brain/logs/nightly.log`.

---

## 7. Verify a run / re-run a missed night
**Check the last run:**
```bash
tail -n 30 /root/bharat-research-brain/logs/nightly.log
# success looks like:  FRESHNESS OK ...   ->   DAILY RUN OK - prices as of ... equity Rs ...
```
**Confirm on Supabase (new equity row):**
```bash
cd /root/bharat-research-brain && . .venv/bin/activate
python - <<'PY'
import asyncio
from backend.db.session import SessionLocal
from sqlalchemy import text
async def m():
    async with SessionLocal() as s:
        for r in (await s.execute(text(
            "select trade_date,total_equity,exposure_level from paper_equity_curve "
            "order by trade_date desc limit 3"))).all():
            print(r)
asyncio.run(m())
PY
```
**Dashboard (Vercel):** the "Real data" latest date advances after each successful run.

**Missed a night?** The chain is **idempotent** — just run it by hand; it fetches + marks
forward to the latest session:
```bash
cd /root/bharat-research-brain && . .venv/bin/activate && python -m scripts.run_daily ; echo "EXIT=$?"
```
(ingest is `ON CONFLICT DO NOTHING`; F+ marks each trading day once — re-runs on an
already-marked day are no-ops.)

---

## Appendix A — dashboard on Vercel (separate from this worker)
Root directory `maven-dashboard`. Env var `DATABASE_URL` = the Supabase **pooler** string
in **plain** `postgresql://` form (NO `+asyncpg`; the `pg` driver enables SSL automatically
for non-localhost). Deploy. Patch Next first: `npm i next@14.2` in `maven-dashboard`.

## Appendix B — security
- `.env` is gitignored and `chmod 600`. **Never commit it.**
- Keep the rotated DB password only in this `.env` and in Vercel's env settings.
- Read-only intent: the worker only writes its own `paper_*` and `prices_eod_adjusted`
  rows. No broker keys, no order placement (this is paper-trading research).

# HOSTED_DB.md — migrate Postgres to the cloud (one DB for the nightly job + Vercel)

The local Docker Postgres can't be reached by a cloud cron job or Vercel. Move to a
hosted Postgres so the always-on nightly engine (and any future dashboard) share one DB.

## Choice: **Neon** (documented)
Picked **Neon** over Supabase: it's plain managed Postgres 16 (no extra auth/Realtime
layer we don't use), has a generous free tier, gives a direct `postgresql://` string,
and supports `pgvector` (needed later for the news embeddings in AGENTS.md §5). Supabase
would also work; the steps below are identical apart from where you copy the string from.

> Only **public market data** leaves this machine (stocks, prices, benchmark index,
> agent score snapshots). **No** broker keys, `.env`, vault notes, or PII — those stay
> local (CLAUDE.md §6). The hosted string lives in `.env` (gitignored), never committed.

## Steps

1. **Create the project** at neon.tech → copy the connection string. Convert it to the
   async driver this app uses:
   ```
   POSTGRES_URL=postgresql+asyncpg://<user>:<pass>@<ep>.neon.tech/<db>?ssl=require
   ```
   Put it in `.env` (local, for the export step) and on the VM/Railway (for prod).

2. **Create the schema on Neon** (all migrations, including `0030_paper_trading`):
   ```bash
   POSTGRES_URL=<neon-async-url> alembic upgrade head
   ```

3. **Copy the data the forward system needs** (schema already exists from step 2 →
   `--data-only`). From the local Docker DB to Neon:
   ```bash
   # dump only the tables the engine reads (public market data)
   docker compose exec -T postgres pg_dump -U bharat -d bharat --data-only --no-owner \
     -t stocks -t indices -t index_constituents \
     -t prices_eod -t prices_eod_adjusted -t benchmark_index \
     -t fundamental_signals_historical -t macro_signals_historical \
     -t sector_signals_historical -t stock_rankings -t trading_calendar \
     > forward_data.sql

   # load into Neon (psql connection string = the non-async form)
   psql "postgresql://<user>:<pass>@<ep>.neon.tech/<db>?sslmode=require" < forward_data.sql
   ```
   (`stocks`/`indices`/`trading_calendar` first if FK order complains; pg_dump orders
   them for you. Large `prices_eod*` may take a few minutes.)

4. **Verify connectivity + data** (read-only smoke test):
   ```bash
   POSTGRES_URL=<neon-async-url> python -m scripts.test_hosted_db
   # expect: connected: PostgreSQL 16 ... ; OK stocks/prices_eod_adjusted/benchmark_index
   ```

5. Both `scripts/nightly_run.py` and any Vercel reader now use this one
   `POSTGRES_URL`. Then go live per **DEPLOY.md** (`paper_inception --commit`).

## Keeping prices fresh on the hosted DB
The nightly EOD price ingest (yfinance/bhavcopy) must write to the **hosted** DB going
forward (point its `POSTGRES_URL` at Neon too), or `nightly_run.py` will have no new
`prices_eod_adjusted` row to mark against. Run ingest **before** `nightly_run.py`.

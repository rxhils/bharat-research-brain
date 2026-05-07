# Phase 1 — Chunk 1.1: Database schema spec

> Status: **operator-approved with amendments**. Spec only. No code, no migrations, no models in this commit.
>
> Scope: 10 tables + Alembic setup + seed data for `indices` and `trading_calendar`. Nothing else.

---

## 0. Conventions baked in (per CLAUDE.md and operator preconditions)

- **Time:** all `*_at` columns are `TIMESTAMPTZ` stored in UTC. Display in IST is the API/dashboard layer's job.
- **Money:** `NUMERIC(18,4)`. No floats anywhere.
- **Volume / counts:** `BIGINT`.
- **Stock identity:** `ISIN` is the canonical key (`VARCHAR(12)`). Symbols are joinable identifiers, never primary.
- **`prices_eod`:** plain (non-partitioned) table for now, but composite PK ordered so future `PARTITION BY RANGE(trade_date)` is non-breaking.
- **Ingestion provenance:** every ingestion writes one row to `data_ingestion_runs` with `source_url`, `source_name`, `downloaded_at_utc`, `file_sha256`, `row_count`, `source_trade_date`. Every `prices_eod` row references that run.
- **Backtest integrity:** queries against `index_constituents` MUST filter `effective_from <= trade_date < effective_to`. Enforced in repository layer, codified in CLAUDE.md §4.
- **Soft-delete:** not used anywhere. Delisted stocks carry `delisted_on`. Index constituents end-date via `effective_to`. No `deleted_at` columns.
- **`updated_at` maintenance:** SQLAlchemy `onupdate=func.now()` on the column. **All updates must flow through the ORM.** No Postgres triggers. Each model docstring restates this contract.
- **Required Postgres extensions:** `pgcrypto` (for `gen_random_uuid()`), `pg_trgm` (for fuzzy company-name search). Installed in the initial migration.

---

## 1. Per-table specs

### 1.1 `stocks` — universe master

**Purpose.** Static-ish record per tradeable equity. One row per ISIN. Mutable fields (sector, mcap, fno flag) updated in place; identity changes (rename, sector reclassification) trigger an SCD Type 2 close-out + insert in `stock_identifiers`.

| Column | Type | Null | Default | Description |
|---|---|---|---|---|
| `isin` | `VARCHAR(12)` | NO | — | Canonical key. INE/INF prefix + 9 alphanumeric + 1 check digit. |
| `nse_symbol` | `VARCHAR(20)` | YES | — | NSE ticker. NULL for BSE-only listings. |
| `bse_symbol` | `VARCHAR(20)` | YES | — | BSE scrip code or symbol. |
| `yfinance_symbol` | `VARCHAR(24)` | YES | — | Cached `<symbol>.NS` / `.BO` form. |
| `company_name` | `VARCHAR(255)` | NO | — | Current legal name. |
| `industry` | `VARCHAR(120)` | YES | — | NSE industry classification. |
| `sector` | `VARCHAR(80)` | YES | — | Coarse bucket (e.g., Energy, Financials). |
| `mcap_category` | `VARCHAR(8)` | YES | — | One of `large` / `mid` / `small` / `micro`. |
| `mcap_inr_cr` | `NUMERIC(18,4)` | YES | — | Latest market cap, INR crore. |
| `listed_on` | `DATE` | YES | — | First listing date. |
| `delisted_on` | `DATE` | YES | — | NULL means active. |
| `is_fno` | `BOOLEAN` | NO | `false` | F&O eligibility. |
| `lot_size_fno` | `INTEGER` | YES | — | Refreshed quarterly. |
| `last_refreshed_at` | `TIMESTAMPTZ` | NO | `now()` | Last time Universe Agent touched this row. |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` | |
| `updated_at` | `TIMESTAMPTZ` | NO | `now()` | Maintained by SQLAlchemy `onupdate=func.now()`; all updates must flow through the ORM. |

**Primary key.** `isin`.
**Foreign keys.** None outbound.
**Indexes.**
- `idx_stocks_nse_symbol_active` — partial unique on `(nse_symbol)` `WHERE delisted_on IS NULL`. Active-symbol uniqueness without blocking historical reuse after delisting.
- `idx_stocks_bse_symbol_active` — partial unique on `(bse_symbol)` `WHERE delisted_on IS NULL`.
- `idx_stocks_sector` — btree on `(sector)`. Sector-scoped scans.
- `idx_stocks_active` — partial btree on `(delisted_on)` `WHERE delisted_on IS NULL`. Cheap "all active stocks" enumeration.
- `idx_stocks_name_trgm` — GIN on `(company_name gin_trgm_ops)`. Fuzzy company-name search; requires `pg_trgm` extension (installed in 0001 migration). Autogenerate-blind — added by hand in the migration.

**Constraints.**
- `CHECK (length(isin) = 12)`
- `CHECK (mcap_category IS NULL OR mcap_category IN ('large','mid','small','micro'))`
- `CHECK (delisted_on IS NULL OR listed_on IS NULL OR delisted_on >= listed_on)`

**Growth.** ~500 active + ~2,000 delisted historical over a decade. Trivial.
**Retention.** Forever. Delisted rows kept for backtests.

---

### 1.2 `stock_identifiers` — SCD Type 2 identity history

**Purpose.** Slowly-changing-dimension log per `(isin, identifier_type)`. Records the value of each identity / classification field across time with explicit `effective_from` / `effective_to` ranges. Supports point-in-time symbol / name / sector queries (backtest reports, historical news matching, research). When the Universe Agent detects a change, it end-dates the current row (sets `effective_to`) and inserts a new row with the new value.

| Column | Type | Null | Default | Description |
|---|---|---|---|---|
| `id` | `BIGSERIAL` | NO | seq | |
| `isin` | `VARCHAR(12)` | NO | — | FK → `stocks(isin)`. |
| `identifier_type` | `VARCHAR(24)` | NO | — | One of `nse_symbol` / `bse_symbol` / `company_name` / `industry` / `sector` / `mcap_category` / `lot_size_fno` / `is_fno`. |
| `value` | `TEXT` | NO | — | Actual symbol / name / sector value during the period. |
| `effective_from` | `DATE` | NO | — | Inclusive start. |
| `effective_to` | `DATE` | YES | — | Exclusive end. NULL = current. |
| `recorded_at` | `TIMESTAMPTZ` | NO | `now()` | Insert time. |
| `source` | `VARCHAR(64)` | NO | — | e.g., `nse_archive`, `openalgo`, `manual`. |

**Primary key.** `id`.
**Foreign keys.**
- `isin` → `stocks(isin)` `ON DELETE CASCADE`. Identity history is rebuildable from sources; cascade matches "stock removed → drop its history rows" intent.

**Indexes.**
- `idx_stock_identifiers_lookup` on `(isin, identifier_type, effective_from DESC)` — main backtest / point-in-time lookup.
- `idx_stock_identifiers_current` partial on `(isin, identifier_type)` `WHERE effective_to IS NULL` — fast "current value of field X for stock Y".
- `idx_stock_identifiers_reverse` on `(identifier_type, value)` — reverse lookup ("which ISIN had symbol RELIANCE on 2018-04-15"); supports historical news matching.

**Constraints.**
- `CHECK (identifier_type IN ('nse_symbol','bse_symbol','company_name','industry','sector','mcap_category','lot_size_fno','is_fno'))`
- `CHECK (effective_to IS NULL OR effective_to > effective_from)`
- `UNIQUE (isin, identifier_type, effective_from)` — same field cannot have two version-starts on the same date.

**Growth.** Initial seed at universe load: ~500 stocks × ~8 fields = ~4,000 rows. Plus ~50–200 changes/year. Trivial.
**Retention.** Forever.

---

### 1.3 `indices` — index registry

**Purpose.** Catalog of indices we track. Static-ish; new entries added when NSE launches a new index.

| Column | Type | Null | Default | Description |
|---|---|---|---|---|
| `index_code` | `VARCHAR(32)` | NO | — | Stable code, e.g., `NIFTY50`, `NIFTYBANK`. |
| `index_name` | `VARCHAR(120)` | NO | — | Display name. |
| `index_type` | `VARCHAR(16)` | NO | — | `broad` / `sector` / `thematic`. |
| `description` | `TEXT` | YES | — | |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` | |
| `updated_at` | `TIMESTAMPTZ` | NO | `now()` | Maintained by SQLAlchemy `onupdate=func.now()`. |

**Primary key.** `index_code`.
**Foreign keys.** None.
**Indexes.** PK only.
**Constraints.**
- `CHECK (index_type IN ('broad','sector','thematic'))`

**Growth.** ~20 rows total, near-static.
**Retention.** Forever.

---

### 1.4 `index_constituents` — slowly-changing membership

**Purpose.** Which stock was in which index, with effective-date ranges. Source of truth for survivorship-bias-free backtests. Append-only with `effective_to` close-out — existing rows are end-dated, never overwritten.

| Column | Type | Null | Default | Description |
|---|---|---|---|---|
| `id` | `BIGSERIAL` | NO | seq | |
| `index_code` | `VARCHAR(32)` | NO | — | FK → `indices(index_code)`. |
| `isin` | `VARCHAR(12)` | NO | — | FK → `stocks(isin)`. |
| `weight_pct` | `NUMERIC(8,4)` | YES | — | Latest published weight, informational. |
| `effective_from` | `DATE` | NO | — | Inclusive start. |
| `effective_to` | `DATE` | YES | — | Exclusive end. NULL = current. |
| `recorded_at` | `TIMESTAMPTZ` | NO | `now()` | |
| `source` | `VARCHAR(64)` | NO | — | |

**Primary key.** `id`.
**Foreign keys.**
- `index_code` → `indices(index_code)` `ON DELETE RESTRICT`. Indices are not deleted.
- `isin` → `stocks(isin)` `ON DELETE RESTRICT`. Survivorship rule — must not lose membership history.

**Indexes.**
- `idx_constituents_lookup` on `(index_code, isin, effective_from DESC)` — main backtest lookup.
- `idx_constituents_active` partial on `(index_code, effective_to)` `WHERE effective_to IS NULL` — fast "current members of index X".
- `idx_constituents_isin_history` on `(isin, effective_from DESC)` — reverse lookup ("which indices does this stock belong to").

**Constraints.**
- `CHECK (effective_to IS NULL OR effective_to > effective_from)`
- `UNIQUE (index_code, isin, effective_from)` — same membership cannot duplicate per start date.

**Growth.** ~7,000 active rows (500 stocks × ~14 indices avg). Quarterly reshuffles add ~200 rows/year. ~10,000 over a decade.
**Retention.** Forever. Survivorship-bias rule depends on it.

---

### 1.5 `prices_eod` — daily OHLCV + delivery

**Purpose.** End-of-day candle per (stock, trading day). Raw values from source; **no `adj_*` columns yet** — adjusted prices arrive in Phase 2.5. Designed partition-ready: composite PK `(trade_date, isin)` aligns with future `PARTITION BY RANGE(trade_date)`.

| Column | Type | Null | Default | Description |
|---|---|---|---|---|
| `trade_date` | `DATE` | NO | — | NSE/BSE trading date. |
| `isin` | `VARCHAR(12)` | NO | — | FK → `stocks(isin)`. |
| `open` | `NUMERIC(18,4)` | YES | — | |
| `high` | `NUMERIC(18,4)` | YES | — | |
| `low` | `NUMERIC(18,4)` | YES | — | |
| `close` | `NUMERIC(18,4)` | YES | — | |
| `prev_close` | `NUMERIC(18,4)` | YES | — | As reported by source. |
| `volume` | `BIGINT` | YES | — | Total traded shares. |
| `turnover_inr` | `NUMERIC(20,4)` | YES | — | Total traded value, INR. |
| `vwap` | `NUMERIC(18,4)` | YES | — | Volume-weighted avg, source-reported. |
| `delivery_qty` | `BIGINT` | YES | — | NSE-specific. |
| `delivery_pct` | `NUMERIC(7,4)` | YES | — | 0–100. |
| `trade_count` | `BIGINT` | YES | — | Number of trades, where reported. |
| `source` | `VARCHAR(32)` | NO | — | `nse_bhavcopy` / `openalgo` / `yfinance`. |
| `ingestion_run_id` | `BIGINT` | NO | — | FK → `data_ingestion_runs(id)`. |
| `inserted_at` | `TIMESTAMPTZ` | NO | `now()` | |

**Primary key.** `(trade_date, isin)`.
**Foreign keys.**
- `isin` → `stocks(isin)` `ON DELETE RESTRICT`. Price history irreplaceable.
- `ingestion_run_id` → `data_ingestion_runs(id)` `ON DELETE RESTRICT`. Provenance must outlive the run row.

**Indexes.**
- PK serves `(trade_date, …)` lookups (daily report pattern).
- `idx_prices_eod_isin_date` on `(isin, trade_date DESC)` — single-stock history.
- `idx_prices_eod_source_date` on `(source, trade_date DESC)` — fallback-source telemetry.

**Constraints.**
- `CHECK (open IS NULL OR open >= 0)`
- `CHECK (high IS NULL OR low IS NULL OR high >= low)`
- `CHECK (delivery_pct IS NULL OR (delivery_pct >= 0 AND delivery_pct <= 100))`
- `CHECK (volume IS NULL OR volume >= 0)`
- `CHECK (source IN ('nse_bhavcopy','openalgo','yfinance'))`

**Growth.** 500 stocks × ~250 trading days = ~125,000 rows/year. ~1.25M over a decade. Comfortable on a single Postgres node, unpartitioned.
**Retention.** Forever.

---

### 1.6 `corporate_actions` — splits, bonuses, dividends

**Purpose.** Authoritative log of share-count and price-continuity events. Drives Phase 2.5 adjusted-price computation. Insert-only; corrections via new row with `description` explaining override.

| Column | Type | Null | Default | Description |
|---|---|---|---|---|
| `id` | `BIGSERIAL` | NO | seq | |
| `isin` | `VARCHAR(12)` | NO | — | FK → `stocks(isin)`. |
| `action_type` | `VARCHAR(16)` | NO | — | `split` / `bonus` / `dividend` / `rights` / `spinoff` / `merger`. |
| `ex_date` | `DATE` | NO | — | First trading day on adjusted basis. |
| `record_date` | `DATE` | YES | — | |
| `announcement_date` | `DATE` | YES | — | |
| `ratio_numerator` | `NUMERIC(12,4)` | YES | — | e.g., split 1:5 → numerator=1. |
| `ratio_denominator` | `NUMERIC(12,4)` | YES | — | e.g., split 1:5 → denominator=5. |
| `amount_inr` | `NUMERIC(18,4)` | YES | — | Per-share dividend / rights subscription price. |
| `description` | `TEXT` | YES | — | Free-form notes. |
| `source` | `VARCHAR(64)` | NO | — | |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` | |

**Primary key.** `id`.
**Foreign keys.**
- `isin` → `stocks(isin)` `ON DELETE RESTRICT`. Action history irreplaceable; required for adjusted-price math.

**Indexes.**
- `idx_ca_isin_exdate` on `(isin, ex_date DESC)`.
- `idx_ca_exdate` on `(ex_date)`.

**Constraints.**
- `CHECK (action_type IN ('split','bonus','dividend','rights','spinoff','merger'))`
- `UNIQUE (isin, action_type, ex_date)`

**Growth.** ~1,000/year across the universe. ~10,000 over a decade.
**Retention.** Forever.

---

### 1.7 `trading_calendar` — exchange open/closed days

**Purpose.** Pre-loaded list of every calendar day per exchange, flagging open vs closed. Universe Agent and Price Agent gate on this.

| Column | Type | Null | Default | Description |
|---|---|---|---|---|
| `trade_date` | `DATE` | NO | — | Calendar date. |
| `exchange` | `VARCHAR(8)` | NO | `'NSE'` | `NSE` or `BSE`. |
| `is_open` | `BOOLEAN` | NO | — | |
| `session_type` | `VARCHAR(16)` | NO | `'regular'` | `regular` / `muhurat` / `closed`. |
| `holiday_name` | `VARCHAR(80)` | YES | — | Canonical name (e.g., "Republic Day", "Diwali"). NULL on weekends and regular trading days. Enables clean joins for "what was the holiday on date X". |
| `notes` | `TEXT` | YES | — | Free-text operational annotations. |
| `created_at` | `TIMESTAMPTZ` | NO | `now()` | |
| `updated_at` | `TIMESTAMPTZ` | NO | `now()` | Maintained by SQLAlchemy `onupdate=func.now()`. |

**Primary key.** `(trade_date, exchange)`.
**Foreign keys.** None.
**Indexes.**
- PK serves direct lookups.
- `idx_calendar_open` partial on `(exchange, trade_date)` `WHERE is_open` — "next/prev trading day" scans.

**Constraints.**
- `CHECK (session_type IN ('regular','muhurat','closed'))`
- `CHECK (exchange IN ('NSE','BSE'))`
- `CHECK (NOT is_open OR session_type <> 'closed')`

**Growth.** ~365 × 2 exchanges = ~730 rows/year. Trivial.
**Retention.** Forever.

---

### 1.8 `data_ingestion_runs` — agent-run provenance

**Purpose.** One row per agent invocation. Captures source, file hash, row counts, status. Every `prices_eod` row points back to a run; every `data_quality_log` event optionally references one.

| Column | Type | Null | Default | Description |
|---|---|---|---|---|
| `id` | `BIGSERIAL` | NO | seq | |
| `agent_name` | `VARCHAR(64)` | NO | — | e.g., `universe`, `price_eod`. |
| `run_id` | `UUID` | NO | `gen_random_uuid()` | Correlation key for structlog. |
| `started_at` | `TIMESTAMPTZ` | NO | `now()` | |
| `finished_at` | `TIMESTAMPTZ` | YES | — | |
| `status` | `VARCHAR(16)` | NO | `'running'` | `running` / `success` / `failed` / `partial`. |
| `source_url` | `TEXT` | YES | — | URL of artifact fetched, if any. |
| `source_name` | `VARCHAR(64)` | YES | — | e.g., `nse_archive`, `openalgo`. |
| `downloaded_at_utc` | `TIMESTAMPTZ` | YES | — | When the artifact was retrieved. |
| `file_sha256` | `CHAR(64)` | YES | — | SHA-256 of downloaded artifact. |
| `row_count` | `BIGINT` | YES | — | Rows ingested. |
| `source_trade_date` | `DATE` | YES | — | Trade date represented by the artifact (bhavcopy). |
| `error_message` | `TEXT` | YES | — | |
| `metadata` | `JSONB` | YES | — | Free-form payload. |

**Primary key.** `id`.
**Foreign keys.** None.
**Indexes.**
- `idx_ingestion_agent_started` on `(agent_name, started_at DESC)`.
- `idx_ingestion_failed` partial on `(status, started_at DESC)` `WHERE status <> 'success'`.
- `uq_ingestion_run_id` unique on `(run_id)`.

**Constraints.**
- `CHECK (status IN ('running','success','failed','partial'))`
- `CHECK (file_sha256 IS NULL OR length(file_sha256) = 64)`

**Growth.** ~10 agents × daily = ~3,650/year. Tiny.
**Retention.** Forever.

---

### 1.9 `data_quality_log` — quality events

**Purpose.** Structured warnings and errors emitted by the Data Quality Agent. Supports queries like "open errors right now" and "all stale-price warnings for ISIN X this month".

| Column | Type | Null | Default | Description |
|---|---|---|---|---|
| `id` | `BIGSERIAL` | NO | seq | |
| `ingestion_run_id` | `BIGINT` | YES | — | FK → `data_ingestion_runs(id)`. NULL for cross-run checks. |
| `isin` | `VARCHAR(12)` | YES | — | FK → `stocks(isin)`. NULL for universe-level events. |
| `severity` | `VARCHAR(8)` | NO | — | `info` / `warn` / `error`. |
| `code` | `VARCHAR(64)` | NO | — | Stable code, e.g., `STALE_PRICE`, `VOLUME_DISCREPANCY`. |
| `message` | `TEXT` | NO | — | Human-readable. |
| `context` | `JSONB` | YES | — | Structured payload. |
| `detected_at` | `TIMESTAMPTZ` | NO | `now()` | |
| `resolved_at` | `TIMESTAMPTZ` | YES | — | NULL = open. |
| `resolved_by` | `VARCHAR(64)` | YES | — | `manual` / `auto` / agent name. |

**Primary key.** `id`.
**Foreign keys.**
- `ingestion_run_id` → `data_ingestion_runs(id)` `ON DELETE SET NULL`. Quality events outlive defective run rows defensively.
- `isin` → `stocks(isin)` `ON DELETE CASCADE`. Quality logs are rebuildable from re-ingestion.

**Indexes.**
- `idx_dql_open` partial on `(severity, detected_at DESC)` `WHERE resolved_at IS NULL`.
- `idx_dql_isin` on `(isin, detected_at DESC)`.
- `idx_dql_code` on `(code, detected_at DESC)`.

**Constraints.**
- `CHECK (severity IN ('info','warn','error'))`

**Growth.** ~50,000/year early, dropping as ops mature.
**Retention.** `error` rows forever; `info`/`warn` archived after 1 year (mechanism deferred).

---

### 1.10 `schema_version` — operational migration history

**Purpose.** Human-readable migration log alongside Alembic's internal `alembic_version` table. Each Alembic migration's final operation writes a row here. Operators run `SELECT * FROM schema_version ORDER BY applied_at` for a one-query summary of project schema history without parsing the migrations folder.

| Column | Type | Null | Default | Description |
|---|---|---|---|---|
| `version_label` | `VARCHAR(32)` | NO | — | Migration label, e.g., `0001_initial_schema`. |
| `applied_at` | `TIMESTAMPTZ` | NO | `now()` | When the migration ran. |
| `description` | `TEXT` | YES | — | Free-form summary. |
| `chunk_reference` | `VARCHAR(32)` | YES | — | e.g., `phase-1-chunk-1.1`. |

**Primary key.** `version_label`.
**Foreign keys.** None.
**Indexes.** PK only.
**Constraints.** None.

**Growth.** ~10–30 rows/year as schema evolves. Trivial.
**Retention.** Forever.

---

## 2. Cross-table

### 2.1 ER diagram

```mermaid
erDiagram
    stocks ||--o{ stock_identifiers : "history"
    stocks ||--o{ index_constituents : "membership"
    stocks ||--o{ prices_eod : "daily candle"
    stocks ||--o{ corporate_actions : "events"
    stocks ||--o{ data_quality_log : "flags"
    indices ||--o{ index_constituents : "members"
    data_ingestion_runs ||--o{ prices_eod : "produced"
    data_ingestion_runs ||--o{ data_quality_log : "spawned"
    trading_calendar {
        date trade_date
        text exchange
    }
    schema_version {
        text version_label
        timestamp applied_at
    }
```

### 2.2 Naming conventions

- **Tables:** `snake_case`. Plural for collections (`stocks`, `indices`, `prices_eod`); the locked list mixes in `trading_calendar`, `data_ingestion_runs`, `data_quality_log`, `schema_version` (singular). Inconsistency accepted under SCOPE LOCK.
- **Columns:** `snake_case`.
- **FK columns:**
  - Surrogate-key FKs end in `_id` (e.g., `ingestion_run_id`).
  - ISIN FKs use the column name `isin` directly.
  - Index-code FKs use `index_code` directly.
- **Booleans:** `is_*` prefix (`is_open`, `is_fno`).
- **Timestamps:** `*_at` for timestamps, `*_date` for dates. `_at` is always `TIMESTAMPTZ` (UTC); `_date` is `DATE`.
- **Status / type / category:** stored as `VARCHAR(...)` plus `CHECK` constraint listing allowed values (no native ENUMs).

### 2.3 Timestamp policy

- **Mutable parent tables** (`stocks`, `indices`, `trading_calendar`): `created_at` + `updated_at`. `updated_at` maintained by SQLAlchemy via `onupdate=func.now()` on the column. **All updates must flow through the ORM** — raw SQL `UPDATE` statements bypass this and must be avoided. Each ORM model docstring restates this contract. No Postgres triggers.
- **Append-only tables** (`stock_identifiers`, `index_constituents`, `prices_eod`, `corporate_actions`, `data_ingestion_runs`, `data_quality_log`): single insertion timestamp only (`recorded_at` / `inserted_at` / `created_at` / `started_at` / `detected_at`). No `updated_at` because rows are never updated.
- **Operational table** (`schema_version`): `applied_at` only (immutable after insert).
- All timestamps stored as `TIMESTAMPTZ` in UTC. IST conversion only at the display layer.

### 2.4 Soft-delete policy

Not used. Justifications:
- `stocks`: delisting modeled semantically via `delisted_on`.
- `index_constituents` and `stock_identifiers`: end-dated via `effective_to`.
- All other tables: append-only, deletion would violate audit guarantees.

If deletion ever becomes necessary (e.g., GDPR-style request — irrelevant here, no PII), it is a manual operations procedure outside the schema's contract.

### 2.5 ON DELETE policy — hybrid

Derived / rebuildable child tables `CASCADE`; precious historical data `RESTRICT`s.

| FK | ON DELETE | Rationale |
|---|---|---|
| `stock_identifiers.isin → stocks.isin` | CASCADE | Identity history rebuildable from sources. |
| `index_constituents.isin → stocks.isin` | RESTRICT | Survivorship-bias rule — must not lose membership history. |
| `index_constituents.index_code → indices.index_code` | RESTRICT | Same. |
| `prices_eod.isin → stocks.isin` | RESTRICT | Price history irreplaceable. |
| `prices_eod.ingestion_run_id → data_ingestion_runs.id` | RESTRICT | Provenance must outlive the run row. |
| `corporate_actions.isin → stocks.isin` | RESTRICT | Action history irreplaceable; required for adjusted-price math. |
| `data_quality_log.isin → stocks.isin` | CASCADE | Quality logs are rebuildable. |
| `data_quality_log.ingestion_run_id → data_ingestion_runs.id` | SET NULL | Quality events outlive defective run rows defensively. |

(Stocks and ingestion-run rows are never deleted by design; these FK behaviors codify what would happen if someone bypassed the contract.)

---

## 3. Migration plan

### 3.1 Creation order (FK dependencies)

1. `schema_version` *(no dependencies)*
2. `stocks`
3. `indices`
4. `trading_calendar`
5. `data_ingestion_runs`
6. `stock_identifiers` *(FK → stocks)*
7. `index_constituents` *(FKs → stocks, indices)*
8. `corporate_actions` *(FK → stocks)*
9. `prices_eod` *(FKs → stocks, data_ingestion_runs)*
10. `data_quality_log` *(FKs → stocks, data_ingestion_runs)*

### 3.2 Seed data

| Seed | Source | Approx rows |
|---|---|---|
| `indices` | Hand-curated list: 4 broad (NIFTY50/100/200/500) + 11 sectoral (NIFTYBANK, NIFTYIT, NIFTYAUTO, NIFTYPHARMA, NIFTYFMCG, NIFTYMETAL, NIFTYENERGY, NIFTYREALTY, NIFTYFINSERVICE, NIFTYMEDIA, NIFTYPSUBANK) | ~15 |
| `trading_calendar` | NSE published holiday list 2024–2027 + BSE holiday list 2024–2027, Saturdays/Sundays = closed, weekday-non-holiday = open, Diwali muhurat sessions = `muhurat`. `holiday_name` populated for every closed/muhurat day. | ~3,000 |
| `index_constituents` | **Deferred to Chunk 1.2** (Universe Agent populates) | 0 |

### 3.3 Alembic autogenerate handling

1. Define ORM in `backend/db/models.py` (canonical schema source per the operator's pick (b)).
2. Configure `alembic/env.py`:
   - `target_metadata = Base.metadata` from `backend/db/models.py`.
   - Use a sync database URL (alembic standard; introspection requires sync). Read from same `.env` but adapter swap (`postgresql+asyncpg://` → `postgresql+psycopg://` for migrations only).
3. `alembic revision --autogenerate -m "0001_initial_schema"` produces structural migration. Hand-review and patch:
   - **Required extensions:** `op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")` (for `gen_random_uuid()`) and `op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")` (for fuzzy company-name search). Both at the top of `upgrade()`.
   - **Partial indexes** — autogenerate sometimes drops the `WHERE` clause. Verify and patch.
   - **`CHECK` constraints** — autogenerate omits some. Verify against the spec.
   - **GIN trigram index** on `stocks.company_name` using `gin_trgm_ops` is autogenerate-blind; add manually.
   - **Final op** in every migration: `op.execute("INSERT INTO schema_version (version_label, description, chunk_reference) VALUES (...)")` recording label, description, and chunk reference.
4. `alembic revision -m "0002_seed_indices"` — manual data migration inserting the ~15 index rows. Final op: `INSERT INTO schema_version`.
5. `alembic revision -m "0003_seed_trading_calendar"` — manual data migration inserting ~3,000 calendar rows. Source data shipped as a CSV in `alembic/seeds/`. Final op: `INSERT INTO schema_version`.
6. `alembic upgrade head` runs cleanly against a fresh Postgres. Verification: `SELECT * FROM schema_version` shows three rows (`0001_initial_schema`, `0002_seed_indices`, `0003_seed_trading_calendar`).

Update path: ORM is the source of truth. Schema changes start with model edits → `alembic revision --autogenerate` → review → commit. Every revision file ends with a `schema_version` insert.

---

## 4. Decisions log (open questions resolved)

| # | Decision | Resolution |
|---|---|---|
| Q1 | `updated_at` maintenance | (b) SQLAlchemy `onupdate=func.now()`. No Postgres triggers. ORM-only updates documented in each model docstring. |
| Q2 | ENUM vs CHECK | (b) `VARCHAR + CHECK`. |
| Q3 | `stock_identifiers` modeling | **(b) SCD Type 2** *(operator override)*. Revised shape applied in §1.2. Rationale: point-in-time symbol lookups are not rare; uniformity with `index_constituents` reduces schema cognitive load. |
| Q4 | `prices_eod` PK ordering | (b) `(trade_date, isin)`. |
| Q5 | Trading calendar coverage | (a) every calendar day. **Addition:** new `holiday_name VARCHAR(80) NULL` column for clean joins; `notes` retained for free-text annotations. |
| Q6 | `data_quality_log.context` | (a) JSONB. |
| Q7 | Numeric precision | (a) `NUMERIC(18,4)`. |
| Q8 | Index code allowlist | (a) free-form. |
| Q9 | ON DELETE behavior | **(c) hybrid** *(operator override)*. Per-FK table in §2.5. |
| Q10 | Naming inconsistency | (a) accept locked names. SCOPE LOCK overrides cosmetic concerns. |
| A1 | Fuzzy name search | `pg_trgm` extension + GIN index on `stocks.company_name gin_trgm_ops`. Codified in §1.1 and §3.3. |
| A2 | Operational migration log | New `schema_version` table (§1.10). Inserted-into by every Alembic migration as its final op. |

---

## 5. Out of scope for Chunk 1.1 (deferred — flagged for AGENTS.md if not already)

- ORM model file `backend/db/models.py` — produced in the Chunk 1.1 *implementation* prompt (next), not in this spec.
- Alembic env config + 0001/0002/0003 migrations — same.
- Universe Agent population logic — Chunk 1.2.
- Adjusted-price columns / corporate-action math — Phase 2.5.
- Index-constituents population (initial load + quarterly refresh) — Chunk 1.2.
- `index_constituents.weight_pct` automation — Chunk 1.2 / 1.5.
- Vault writer + stock-note generation — Chunk 1.6 (reordered after Price Agent).
- Live tick / intraday tables — Phase 2.

---

*End of spec. Status: operator-approved with amendments. Awaiting authorization for the Chunk 1.1 implementation prompt (ORM models + Alembic env + 0001 / 0002 / 0003 migrations).*

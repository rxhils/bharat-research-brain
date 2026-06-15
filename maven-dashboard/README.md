# Maven — Bharat Brain F+ dashboard

A clean 2-screen dashboard for the F+ paper-trading system. **Portfolio** (the what)
and **Brain** (the why), one nav toggle. Runs on **mock data immediately**; becomes
real by swapping the queries — no UI changes.

## Run

```bash
cd maven-dashboard
npm install
npm run dev          # http://localhost:3000
```

Stack: Next.js 14 (App Router) + TypeScript + Tailwind + Recharts. Dark, emerald
accent, Indian formatting (₹ lakh/crore, NSE tickers). Vercel-deployable as-is
(mock data needs no DB).

## Screens
- **Portfolio** (`app/page.tsx`): headline value vs ₹10L, F+ vs Nifty 500 TRI equity
  curve, exposure gauge (100/50/25% + regime), risk-first key stats (max drawdown,
  Sharpe), sortable holdings (25 + cash).
- **Brain** (`app/brain/page.tsx`): A/B "is it working?" (F+ mechanical vs agentic),
  score breakdown (sub-signals to composite), top scores (filterable), and the **Agent
  Activity** board — live status/progress per agent, polled every 4s via `/api/agents`.

## Swap mock to real (the only change needed)

1. **Provision the hosted DB** (Neon — see the repo root `HOSTED_DB.md`) and set:
   ```bash
   # maven-dashboard/.env.local   (gitignored)
   DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/bharat?sslmode=require
   ```
2. **Add a Postgres client:** `npm install pg @types/pg`.
3. **Replace the `TODO(real)` blocks in `lib/data.ts`.** Each function returns mock
   today and has the exact SQL in a comment. Example:
   ```ts
   // before (mock):
   export async function getAccount() { return { ...mock }; }
   // after (real):
   import { Pool } from "pg";
   const pool = new Pool({ connectionString: process.env.DATABASE_URL });
   export async function getAccount() {
     const { rows } = await pool.query("SELECT * FROM paper_account LIMIT 1");
     return mapAccount(rows[0]);   // shape already defined in lib/types.ts
   }
   ```
   The return **shapes never change** (defined in `lib/types.ts`), so no component edits.
4. The Agent Activity board goes live automatically once the backend writes
   `agent_run_log` (migration `0031` in the repo) — `getAgentBoard()` just reads it.

## Expected backend tables (from the paper engine)
| Table | Used for |
|---|---|
| `paper_account` | headline value, cash, inception, engine version |
| `paper_equity_curve` | equity curve, drawdown, exposure, Nifty 500 TRI |
| `paper_position` | holdings table (status open) |
| `agent_score_snapshot` | Brain: composite + sub-signal scores per stock |
| `agent_run_log` | Agent Activity board (live heartbeat) |
| `stocks` | ticker / name / sector joins |
| `benchmark_index` | Nifty 500 TRI series + regime derivation |

## Notes / honest framing
- The track record is **paper, forward, starts at inception** — not backfilled. The
  UI labels it so, and frames **risk (drawdown, exposure)** as the headline, not
  "beats the market" (F+'s real claim is index-like return with ~half the drawdown).
- Until the News / FMP / FII agents are wired, the **agentic** A/B line and the
  News/Sentiment sub-scores show as "coming / pending"; the record tests F+ on the
  **mechanical composite** (the validated signal). No backend or F+ code is touched
  by this dashboard.

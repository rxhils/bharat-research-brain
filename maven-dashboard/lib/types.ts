// Table shapes mirroring the Bharat Brain paper-engine DB (migration 0030/0031).
// The dashboard reads these read-only. Column names match the SQL so wiring the
// real queries in lib/data.ts is a 1:1 mapping.

export type Regime = "risk_on" | "risk_off";
export type Signal = "bullish" | "neutral" | "avoid";
export type ScoreSource = "mechanical" | "agentic";

// paper_account (singleton)
export interface PaperAccount {
  inceptionDate: string;        // inception_date
  startingCapital: number;      // starting_capital (1000000)
  currentCash: number;          // current_cash
  currentEquity: number;        // current_equity
  lastUpdated: string;          // last_updated
  engineVersion: string;        // engine_version ("F+ 57e72d5")
  scoreSource: ScoreSource;     // score_source
}

// paper_position (status='open')
export interface Holding {
  isin: string;
  ticker: string;               // stocks.nse_symbol
  name: string;                 // stocks.name
  sector: string;               // stocks.sector
  entryDate: string;            // entry_date
  entryPrice: number;           // entry_price
  currentPrice: number;         // latest prices_eod_adjusted.adj_close
  shares: number;               // shares
  weightPct: number;            // shares*current / total_equity
  pnlPct: number;               // current/entry - 1
  isCash?: boolean;             // synthetic cash row
}

// paper_equity_curve (one row per trading day)
export interface EquityPoint {
  date: string;                 // trade_date
  fplus: number;                // total_equity (mechanical book)
  nifty500: number;             // nifty500_tri normalised to inception capital
  fplusAgentic?: number | null; // total_equity of the agentic-fed book (null until live)
  exposure?: number;            // exposure_level
}

export interface ExposureState {
  level: 1 | 0.5 | 0.25;        // exposure_level
  regime: Regime;
  cashPct: number;              // (1-level)*100
}

export interface KeyStats {
  totalReturnPct: number;
  alphaVsNifty500Pct: number;
  maxDrawdownPct: number;       // headline risk metric
  sharpe: number;
  holdings: number;
  winRatePct: number;
  daysLive: number;
}

// agent_score_snapshot (per stock, per run_date) — the "why"
export interface ScoreRow {
  isin: string;
  ticker: string;
  name: string;
  sector: string;
  composite: number;            // composite_score
  momentum: number;             // sub-signals 0..100
  quality: number;
  news: number | null;          // null = agent offline (no data yet)
  sentiment: number | null;
  sectorScore: number;
  signal: Signal;               // signal_label
}

// agent_run_log (live observability heartbeat) — migration 0031
export type AgentStatus = "done" | "running" | "waiting" | "offline" | "error";
export type AgentGroup = "selection" | "market" | "meta";
export interface AgentRun {
  runId: string;                // run_id
  agentName: string;            // agent_name
  group: AgentGroup;            // derived grouping
  status: AgentStatus;          // status
  progressCurrent: number | null; // progress_current
  progressTotal: number | null;   // progress_total
  headlineOutput: string;       // headline_output ("scored 507 stocks")
  startedAt: string | null;     // started_at
  finishedAt: string | null;    // finished_at
  durationMs: number | null;    // duration_ms
  offlineReason?: string;       // why (when status=offline)
}

export interface AgentBoard {
  runId: string;
  lastRun: string;              // human timestamp
  inProgress: boolean;          // any agent running -> poll
  agents: AgentRun[];
}

// A/B: do the agents add value?
export interface ABReadout {
  hasAgentic: boolean;          // false until the agentic book goes live
  edgePct: number | null;       // agentic - mechanical, full period
  note: string;
}

// One trade (paper_position row) + its price path, for the Trades page.
export interface TradePoint {
  date: string;                 // trade_date
  close: number;                // adj_close
}
export interface Trade {
  id: number;
  isin: string;
  ticker: string;               // stocks.nse_symbol
  name: string;                 // stocks.company_name
  sector: string;
  status: "open" | "closed";
  entryDate: string;            // entry_date
  entryPrice: number;           // entry_price
  exitDate: string | null;      // exit_date
  exitPrice: number | null;     // exit_price
  exitReason: string | null;    // exit_reason: breakdown | rebalance
  currentPrice: number;         // latest adj_close (open) or exit_price (closed)
  shares: number;
  pnlPct: number;               // current/entry - 1
  exposureAtEntry: number;      // exposure_at_entry
  whyEntry: string;             // plain-English: why F+ bought
  whyExit: string | null;       // plain-English: why F+ sold (closed only)
  series: TradePoint[];         // adj_close entry -> exit/latest (sparkline)
  trendPct: number;             // last vs first of series (day-to-day direction)
}

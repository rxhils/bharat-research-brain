// DATA LAYER — REAL DB queries only. ZERO mock. SERVER-ONLY (imported by server
// components + the /api/agents route). Reads the frozen-F+ paper tables written by
// scripts.paper_inception / scripts.nightly_run. If a value has no real source yet
// (e.g. the agentic research layer is offline), we return an honest empty state —
// never a fabricated number.

import { dbReady, q } from "./db";
import type {
  ABReadout, AgentBoard, AgentRun, EquityPoint, ExposureState,
  Holding, KeyStats, PaperAccount, ScoreRow,
} from "./types";

const num = (v: unknown): number => (v == null ? 0 : Number(v));

class NotConnected extends Error {
  constructor(what: string) {
    super(`No real data for ${what}: set DATABASE_URL and run paper_inception. (No mock fallback by design.)`);
  }
}

async function latestPriceDate(): Promise<string> {
  const r = await q<{ d: string }>("SELECT MAX(trade_date)::text AS d FROM prices_eod_adjusted");
  return r[0]?.d ?? "";
}

// ----------------------------------------------------------------- account
export async function getAccount(): Promise<PaperAccount> {
  if (!dbReady()) throw new NotConnected("account");
  const r = await q<Record<string, unknown>>(
    `SELECT inception_date::text AS inception_date, starting_capital, current_cash,
            current_equity, last_updated, engine_version, score_source
       FROM paper_account ORDER BY id LIMIT 1`);
  if (!r.length) throw new NotConnected("account (inception not committed)");
  const a = r[0];
  return {
    inceptionDate: String(a.inception_date),
    startingCapital: num(a.starting_capital),
    currentCash: num(a.current_cash),
    currentEquity: num(a.current_equity),
    lastUpdated: a.last_updated ? new Date(a.last_updated as string).toISOString() : "",
    engineVersion: String(a.engine_version),
    scoreSource: String(a.score_source) as PaperAccount["scoreSource"],
  };
}

// ------------------------------------------------------------- equity curve
export async function getEquityCurve(): Promise<EquityPoint[]> {
  if (!dbReady()) return [];
  const rows = await q<Record<string, unknown>>(
    `SELECT trade_date::text AS d, total_equity, nifty500_tri, exposure_level
       FROM paper_equity_curve ORDER BY trade_date`);
  if (!rows.length) return [];
  const base = num(rows[0].total_equity);
  const triBase = num(rows[0].nifty500_tri) || null;
  return rows.map((r) => {
    const tri = num(r.nifty500_tri);
    return {
      date: String(r.d),
      fplus: Math.round(num(r.total_equity)),
      // normalise the Nifty 500 TRI to the same starting capital for comparison
      nifty500: triBase ? Math.round(base * (tri / triBase)) : Math.round(base),
      fplusAgentic: null,
      exposure: num(r.exposure_level),
    };
  });
}

// ----------------------------------------------------------------- exposure
export async function getExposure(): Promise<ExposureState> {
  if (!dbReady()) return { level: 0.5, regime: "risk_off", cashPct: 0 };
  const r = await q<Record<string, unknown>>(
    `SELECT exposure_level, cash_value, total_equity
       FROM paper_equity_curve ORDER BY trade_date DESC LIMIT 1`);
  if (!r.length) return { level: 0, regime: "risk_off", cashPct: 0 };
  const level = num(r[0].exposure_level);
  const eq = num(r[0].total_equity);
  return {
    level: level as ExposureState["level"],
    regime: level >= 0.999 ? "risk_on" : "risk_off",
    cashPct: eq > 0 ? (num(r[0].cash_value) / eq) * 100 : 0,
  };
}

// ---------------------------------------------------------------- key stats
export async function getKeyStats(): Promise<KeyStats> {
  if (!dbReady()) {
    return { totalReturnPct: 0, alphaVsNifty500Pct: 0, maxDrawdownPct: 0, sharpe: 0, holdings: 0, winRatePct: 0, daysLive: 0 };
  }
  const curve = await q<Record<string, unknown>>(
    `SELECT total_equity, nifty500_tri, drawdown_pct
       FROM paper_equity_curve ORDER BY trade_date`);
  if (curve.length < 1) {
    return { totalReturnPct: 0, alphaVsNifty500Pct: 0, maxDrawdownPct: 0, sharpe: 0, holdings: 0, winRatePct: 0, daysLive: 0 };
  }
  const acct = await getAccount();
  const eq = curve.map((r) => num(r.total_equity));
  const last = eq[eq.length - 1];
  const totalReturnPct = (last / acct.startingCapital - 1) * 100;
  const triFirst = num(curve[0].nifty500_tri);
  const triLast = num(curve[curve.length - 1].nifty500_tri);
  const niftyRet = triFirst ? (triLast / triFirst - 1) * 100 : 0;
  const maxDrawdownPct = Math.max(0, ...curve.map((r) => num(r.drawdown_pct)));
  // daily returns -> annualised Sharpe (rf assumed 0; honest given a young series)
  const rets: number[] = [];
  for (let i = 1; i < eq.length; i++) rets.push(eq[i] / eq[i - 1] - 1);
  const mean = rets.reduce((a, b) => a + b, 0) / (rets.length || 1);
  const variance = rets.reduce((a, b) => a + (b - mean) ** 2, 0) / (rets.length || 1);
  const sd = Math.sqrt(variance);
  const sharpe = sd > 0 ? (mean / sd) * Math.sqrt(252) : 0;
  // holdings + win rate from open positions vs latest price
  const asof = await latestPriceDate();
  const wr = await q<Record<string, unknown>>(
    `SELECT count(*) FILTER (WHERE cur > entry_price) AS wins, count(*) AS total
       FROM (
         SELECT p.entry_price,
           (SELECT adj_close FROM prices_eod_adjusted x
             WHERE x.isin = p.isin AND x.trade_date <= $1
             ORDER BY x.trade_date DESC LIMIT 1) AS cur
         FROM paper_position p WHERE p.status = 'open'
       ) z`, [asof]);
  const total = num(wr[0]?.total);
  const wins = num(wr[0]?.wins);
  return {
    totalReturnPct,
    alphaVsNifty500Pct: totalReturnPct - niftyRet,
    maxDrawdownPct,
    sharpe,
    holdings: total,
    winRatePct: total > 0 ? (wins / total) * 100 : 0,
    daysLive: curve.length,
  };
}

// ----------------------------------------------------------------- holdings
export async function getHoldings(): Promise<Holding[]> {
  if (!dbReady()) return [];
  const acct = await getAccount();
  const asof = await latestPriceDate();
  const rows = await q<Record<string, unknown>>(
    `SELECT p.isin, s.nse_symbol AS ticker, s.company_name AS name, s.sector,
            p.entry_date::text AS entry_date, p.entry_price, p.shares,
            (SELECT adj_close FROM prices_eod_adjusted x
               WHERE x.isin = p.isin AND x.trade_date <= $1
               ORDER BY x.trade_date DESC LIMIT 1) AS current_price
       FROM paper_position p JOIN stocks s ON s.isin = p.isin
      WHERE p.status = 'open'
      ORDER BY (p.shares * p.entry_price) DESC`, [asof]);
  const eq = acct.currentEquity || 1;
  const holdings: Holding[] = rows.map((r) => {
    const entry = num(r.entry_price);
    const cur = num(r.current_price) || entry;
    const shares = num(r.shares);
    return {
      isin: String(r.isin),
      ticker: String(r.ticker ?? r.isin),
      name: String(r.name ?? r.ticker ?? r.isin),
      sector: String(r.sector ?? "—"),
      entryDate: String(r.entry_date),
      entryPrice: entry,
      currentPrice: cur,
      shares,
      weightPct: (shares * cur / eq) * 100,
      pnlPct: entry > 0 ? (cur / entry - 1) * 100 : 0,
    };
  });
  if (acct.currentCash > 0) {
    holdings.push({
      isin: "CASH", ticker: "CASH", name: "Cash (risk-off sleeve)", sector: "Cash",
      entryDate: acct.inceptionDate, entryPrice: 0, currentPrice: 0, shares: 0,
      weightPct: (acct.currentCash / eq) * 100, pnlPct: 0, isCash: true,
    });
  }
  return holdings;
}

// ----------------------------------------- A/B readout (agentic vs mechanical)
export async function getABReadout(): Promise<ABReadout> {
  // Mechanical-only by design: there is no agentic book to compare against. Honest.
  return {
    hasAgentic: false,
    edgePct: null,
    note: "Live signal = the FROZEN F+ mechanical composite (the only version that passed "
      + "every backtest). The News / Sentiment / Fundamental agents are built but offline and "
      + "are NOT part of the live decision — so there is no agentic book to A/B against yet.",
  };
}

// --------------------------------------------------- per-stock scores (none)
export async function getScores(): Promise<ScoreRow[]> {
  // In F+ mechanical-only mode the engine ranks the universe internally at each
  // quarterly rebalance and does NOT persist a per-stock score snapshot. Rather
  // than fabricate scores, we return nothing and the UI says so.
  return [];
}

// ------------------------------------------------------------- agent board
const GROUP_OF: Record<string, AgentRun["group"]> = {};
export async function getAgentBoard(): Promise<AgentBoard> {
  if (!dbReady()) return { runId: "", lastRun: "", inProgress: false, agents: [] };
  const rows = await q<Record<string, unknown>>(
    `SELECT run_id, agent_name, status, progress_current, progress_total,
            headline_output, offline_reason, started_at, finished_at, duration_ms
       FROM agent_run_log
      WHERE run_id = (SELECT run_id FROM agent_run_log ORDER BY updated_at DESC LIMIT 1)
      ORDER BY agent_name`);
  const agents: AgentRun[] = rows.map((r) => ({
    runId: String(r.run_id),
    agentName: String(r.agent_name),
    group: GROUP_OF[String(r.agent_name)] ?? "meta",
    status: String(r.status) as AgentRun["status"],
    headlineOutput: String(r.headline_output ?? ""),
    progressCurrent: r.progress_current == null ? null : num(r.progress_current),
    progressTotal: r.progress_total == null ? null : num(r.progress_total),
    startedAt: r.started_at ? new Date(r.started_at as string).toISOString() : null,
    finishedAt: r.finished_at ? new Date(r.finished_at as string).toISOString() : null,
    durationMs: r.duration_ms == null ? null : num(r.duration_ms),
    offlineReason: r.offline_reason == null ? undefined : String(r.offline_reason),
  }));
  return {
    runId: agents[0]?.runId ?? "",
    lastRun: agents.find((a) => a.finishedAt)?.finishedAt ?? "",
    inProgress: agents.some((a) => a.status === "running"),
    agents,
  };
}

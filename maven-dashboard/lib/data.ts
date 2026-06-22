// DATA LAYER — REAL DB queries only. ZERO mock. SERVER-ONLY (imported by server
// components + the /api/agents route). Reads the frozen-F+ paper tables written by
// scripts.paper_inception / scripts.nightly_run. If a value has no real source yet
// (e.g. the agentic research layer is offline), we return an honest empty state —
// never a fabricated number.

import { dbReady, q } from "./db";
import type {
  ABReadout, AgentBoard, AgentRun, EquityPoint, ExposureState,
  Holding, KeyStats, PaperAccount, ScoreRow, Trade, TradePoint,
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

// The dashboard always shows the LIVE portfolio (currently "Quant" = Enhanced F+).
// After the multi-portfolio migration (0032) paper_* rows are tagged by portfolio_id,
// so every book query is scoped to this id — never the archived F+ classic book.
async function livePortfolioId(): Promise<number | null> {
  const r = await q<{ id: number }>(
    "SELECT id FROM portfolios WHERE status = 'live' ORDER BY id LIMIT 1");
  return r[0]?.id == null ? null : Number(r[0].id);
}

/** All live portfolios (for the portfolio switcher), in display order. */
export async function getLivePortfolios(): Promise<{ id: number; name: string }[]> {
  if (!dbReady()) return [];
  const r = await q<{ id: number; name: string }>(
    "SELECT id, name FROM portfolios WHERE status = 'live' ORDER BY id");
  return r.map((x) => ({ id: Number(x.id), name: String(x.name) }));
}

// ----------------------------------------------------------------- account
export async function getAccount(portfolioId?: number): Promise<PaperAccount> {
  if (!dbReady()) throw new NotConnected("account");
  const pid = portfolioId ?? (await livePortfolioId());
  if (pid == null) throw new NotConnected("account (no live portfolio)");
  const r = await q<Record<string, unknown>>(
    `SELECT inception_date::text AS inception_date, starting_capital, current_cash,
            current_equity, last_updated, engine_version, score_source
       FROM paper_account WHERE portfolio_id = $1 ORDER BY id LIMIT 1`, [pid]);
  if (!r.length) throw new NotConnected("account (no live book yet)");
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
export async function getEquityCurve(portfolioId?: number): Promise<EquityPoint[]> {
  if (!dbReady()) return [];
  const pid = portfolioId ?? (await livePortfolioId());
  if (pid == null) return [];
  const rows = await q<Record<string, unknown>>(
    `SELECT trade_date::text AS d, total_equity, nifty500_tri, exposure_level
       FROM paper_equity_curve WHERE portfolio_id = $1 ORDER BY trade_date`, [pid]);
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
export async function getExposure(portfolioId?: number): Promise<ExposureState> {
  if (!dbReady()) return { level: 0.5, regime: "risk_off", cashPct: 0 };
  const pid = portfolioId ?? (await livePortfolioId());
  // No live book / no curve row yet = created but first allocation hasn't run → 100% cash.
  if (pid == null) return { level: 0.25, regime: "risk_off", cashPct: 100 };
  const r = await q<Record<string, unknown>>(
    `SELECT exposure_level, cash_value, total_equity
       FROM paper_equity_curve WHERE portfolio_id = $1 ORDER BY trade_date DESC LIMIT 1`, [pid]);
  if (!r.length) return { level: 0.25, regime: "risk_off", cashPct: 100 };
  const level = num(r[0].exposure_level);
  const eq = num(r[0].total_equity);
  return {
    level: level as ExposureState["level"],
    regime: level >= 0.999 ? "risk_on" : "risk_off",
    cashPct: eq > 0 ? (num(r[0].cash_value) / eq) * 100 : 0,
  };
}

// ---------------------------------------------------------------- key stats
export async function getKeyStats(portfolioId?: number): Promise<KeyStats> {
  if (!dbReady()) {
    return { totalReturnPct: 0, alphaVsNifty500Pct: 0, maxDrawdownPct: 0, sharpe: 0, holdings: 0, winRatePct: 0, daysLive: 0 };
  }
  const pid = portfolioId ?? (await livePortfolioId());
  const curve = pid == null ? [] : await q<Record<string, unknown>>(
    `SELECT total_equity, nifty500_tri, drawdown_pct
       FROM paper_equity_curve WHERE portfolio_id = $1 ORDER BY trade_date`, [pid]);
  if (curve.length < 1) {
    return { totalReturnPct: 0, alphaVsNifty500Pct: 0, maxDrawdownPct: 0, sharpe: 0, holdings: 0, winRatePct: 0, daysLive: 0 };
  }
  const acct = await getAccount(pid ?? undefined);
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
         FROM paper_position p WHERE p.status = 'open' AND p.portfolio_id = $2
       ) z`, [asof, pid]);
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
export async function getHoldings(portfolioId?: number): Promise<Holding[]> {
  if (!dbReady()) return [];
  const pid = portfolioId ?? (await livePortfolioId());
  const acct = await getAccount(pid ?? undefined);
  const asof = await latestPriceDate();
  const rows = pid == null ? [] : await q<Record<string, unknown>>(
    `SELECT p.isin, s.nse_symbol AS ticker, s.company_name AS name, s.sector,
            p.entry_date::text AS entry_date, p.entry_price, p.shares,
            (SELECT adj_close FROM prices_eod_adjusted x
               WHERE x.isin = p.isin AND x.trade_date <= $1
               ORDER BY x.trade_date DESC LIMIT 1) AS current_price
       FROM paper_position p JOIN stocks s ON s.isin = p.isin
      WHERE p.status = 'open' AND p.portfolio_id = $2
      ORDER BY (p.shares * p.entry_price) DESC`, [asof, pid]);
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
    note: "Live signal = the FROZEN Enhanced F+ composite (the only version that passed "
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

// ------------------------------------------------------------- trades (audit)
export async function getTrades(portfolioId?: number): Promise<Trade[]> {
  if (!dbReady()) return [];
  const asof = await latestPriceDate();
  const pid = portfolioId ?? (await livePortfolioId());
  if (pid == null) return [];
  let inception = "";
  try { inception = (await getAccount(pid)).inceptionDate; } catch { /* no account yet */ }

  const pos = await q<Record<string, unknown>>(
    `SELECT p.id, p.isin, s.nse_symbol AS ticker, s.company_name AS name, s.sector,
            p.entry_date::text AS entry_date, p.entry_price, p.shares, p.exposure_at_entry,
            p.status, p.exit_date::text AS exit_date, p.exit_price, p.exit_reason,
            (SELECT adj_close FROM prices_eod_adjusted x
               WHERE x.isin = p.isin AND x.trade_date <= $1
               ORDER BY x.trade_date DESC LIMIT 1) AS latest_close
       FROM paper_position p JOIN stocks s ON s.isin = p.isin
      WHERE p.portfolio_id = $2
      ORDER BY (p.status = 'open') DESC,
               COALESCE(p.exit_date, $1::date) DESC, p.entry_date DESC`, [asof, pid]);
  if (!pos.length) return [];

  // one query for every involved stock's price path, from the earliest entry
  const isins = Array.from(new Set(pos.map((r) => String(r.isin))));
  const minEntry = pos.reduce(
    (m, r) => (String(r.entry_date) < m ? String(r.entry_date) : m),
    String(pos[0].entry_date));
  const series = await q<Record<string, unknown>>(
    `SELECT isin, trade_date::text AS d, adj_close
       FROM prices_eod_adjusted
      WHERE isin = ANY($1) AND trade_date >= $2
      ORDER BY isin, trade_date`, [isins, minEntry]);
  const byIsin = new Map<string, TradePoint[]>();
  for (const r of series) {
    const k = String(r.isin);
    if (!byIsin.has(k)) byIsin.set(k, []);
    byIsin.get(k)!.push({ date: String(r.d), close: num(r.adj_close) });
  }

  return pos.map((r) => {
    const isin = String(r.isin);
    const status = (String(r.status) === "open" ? "open" : "closed") as Trade["status"];
    const entry = num(r.entry_price);
    const exitPrice = r.exit_price == null ? null : num(r.exit_price);
    const current = status === "open" ? (num(r.latest_close) || entry) : (exitPrice ?? entry);
    const entryDate = String(r.entry_date);
    const exitDate = r.exit_date == null ? null : String(r.exit_date);
    const exposure = num(r.exposure_at_entry);
    const all = byIsin.get(isin) ?? [];
    const hi = exitDate ?? asof;
    const slice = all.filter((p) => p.date >= entryDate && p.date <= hi);
    const trendPct = slice.length >= 2
      ? (slice[slice.length - 1].close / slice[0].close - 1) * 100 : 0;

    const isInception = entryDate === inception;
    const whyEntry = `${isInception ? "Enhanced F+ inception pick" : "Enhanced F+ quarterly rebalance pick"} on `
      + `${entryDate}: ranked in the top names by the Enhanced F+ composite (vol-adjusted momentum + quality `
      + `+ low-volatility), within the ≤4-per-sector cap, bought at ${exposure} exposure.`;
    let whyExit: string | null = null;
    if (status === "closed") {
      const reason = String(r.exit_reason ?? "");
      whyExit = reason === "breakdown"
        ? `Stop hit on ${exitDate}: fell ≥15% below entry (cut-on-breakdown) to protect capital.`
        : reason === "rebalance"
          ? `Sold on ${exitDate}: dropped out of the Enhanced F+ top names at the quarterly rebalance.`
          : `Closed on ${exitDate}${reason ? ` (${reason})` : ""}.`;
    }
    return {
      id: num(r.id), isin, ticker: String(r.ticker ?? isin), name: String(r.name ?? isin),
      sector: String(r.sector ?? "—"), status, entryDate, entryPrice: entry, exitDate, exitPrice,
      exitReason: r.exit_reason == null ? null : String(r.exit_reason),
      currentPrice: current, shares: num(r.shares),
      pnlPct: entry > 0 ? (current / entry - 1) * 100 : 0,
      exposureAtEntry: exposure, whyEntry, whyExit, series: slice, trendPct,
    };
  });
}

// ----------------------------------------------------- data provenance (proof)
// A live "this is real" stamp: counts + latest date read straight from the DB on
// every page load. The latest date advances each time ingest_eod runs — mock can't.
export async function getDataStatus(): Promise<{
  source: string; priceRows: number; stocks: number; latestPrice: string;
}> {
  if (!dbReady()) return { source: "not connected", priceRows: 0, stocks: 0, latestPrice: "" };
  const r = await q<Record<string, unknown>>(
    `SELECT (SELECT count(*) FROM prices_eod_adjusted) AS rows,
            (SELECT count(DISTINCT isin) FROM prices_eod_adjusted) AS stocks,
            (SELECT max(trade_date)::text FROM prices_eod_adjusted) AS latest`);
  const a = r[0] ?? {};
  return {
    source: "Postgres · prices_eod_adjusted (yfinance EOD)",
    priceRows: num(a.rows),
    stocks: num(a.stocks),
    latestPrice: String(a.latest ?? ""),
  };
}

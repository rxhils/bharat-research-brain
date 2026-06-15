// DATA LAYER — mock now, real later.
// Every function returns realistic MOCK data today so the UI is fully functional.
// To go live: set DATABASE_URL and replace each TODO(real) block with the SQL
// (a `pg` Pool query). The return shapes never change, so the UI needs no edits.

import type {
  ABReadout, AgentBoard, AgentRun, EquityPoint, ExposureState,
  Holding, KeyStats, PaperAccount, ScoreRow,
} from "./types";

const INCEPTION = "2026-04-15";
const CAPITAL = 1_000_000;

export async function getAccount(): Promise<PaperAccount> {
  // TODO(real): SELECT * FROM paper_account LIMIT 1
  return {
    inceptionDate: INCEPTION, startingCapital: CAPITAL, currentCash: 500_000,
    currentEquity: 1_041_800, lastUpdated: "2026-05-26T16:05:00+05:30",
    engineVersion: "F+ 57e72d5", scoreSource: "mechanical",
  };
}

function buildCurve(): EquityPoint[] {
  // Deterministic mock: F+ index-like return with ~half the volatility/drawdown.
  const pts: EquityPoint[] = [];
  let f = CAPITAL, n = CAPITAL;
  const d = new Date(INCEPTION);
  for (let i = 0; i < 30; i++) {
    const mkt = Math.sin(i / 3) * 0.011 + 0.0016;
    n *= 1 + mkt;
    f *= 1 + mkt * 0.55 + 0.0006;
    const dt = new Date(d);
    dt.setDate(dt.getDate() + Math.round(i * 1.45));
    pts.push({
      date: dt.toISOString().slice(0, 10),
      fplus: Math.round(f), nifty500: Math.round(n),
      fplusAgentic: null, exposure: i > 18 ? 0.5 : 1,
    });
  }
  return pts;
}
export async function getEquityCurve(): Promise<EquityPoint[]> {
  // TODO(real): SELECT trade_date, total_equity, nifty500_tri, exposure_level
  //             FROM paper_equity_curve ORDER BY trade_date
  return buildCurve();
}

export async function getExposure(): Promise<ExposureState> {
  // TODO(real): latest paper_equity_curve.exposure_level + regime from benchmark_index
  return { level: 0.5, regime: "risk_off", cashPct: 50 };
}

export async function getKeyStats(): Promise<KeyStats> {
  // TODO(real): from paper_equity_curve (maxDD, sharpe) + paper_position (holdings, win rate)
  return {
    totalReturnPct: 4.18, alphaVsNifty500Pct: -1.4, maxDrawdownPct: 6.2,
    sharpe: 0.71, holdings: 25, winRatePct: 56, daysLive: 41,
  };
}

const RAW: [string, string, string, number, number][] = [
  ["ZYDUSLIFE", "Zydus Lifesciences", "Pharma", 1079.05, 1131.4],
  ["GESHIP", "Great Eastern Shipping", "Services", 1650.7, 1583.2],
  ["AJANTPHARM", "Ajanta Pharma", "Pharma", 3097.1, 3260.0],
  ["SUZLON", "Suzlon Energy", "Capital Goods", 54.58, 59.1],
  ["NAVINFLUOR", "Navin Fluorine", "Chemicals", 7396.0, 7180.5],
  ["EICHERMOT", "Eicher Motors", "Auto", 7376.0, 7702.0],
  ["SCI", "Shipping Corp", "Services", 308.05, 297.4],
  ["INDUSTOWER", "Indus Towers", "Telecom", 433.25, 451.8],
  ["MMTC", "MMTC", "Services", 65.04, 71.2],
  ["TRITURBINE", "Triveni Turbine", "Capital Goods", 690.45, 712.3],
  ["WELCORP", "Welspun Corp", "Capital Goods", 1319.0, 1284.0],
  ["MARICO", "Marico", "FMCG", 830.0, 858.6],
  ["KPIL", "Kalpataru Projects", "Construction", 1297.1, 1340.5],
  ["HINDZINC", "Hindustan Zinc", "Metals", 647.4, 631.0],
  ["PIDILITIND", "Pidilite", "Chemicals", 1478.5, 1502.2],
  ["DIVISLAB", "Divis Labs", "Pharma", 6753.0, 6990.0],
  ["3MINDIA", "3M India", "Diversified", 33100.0, 32550.0],
  ["CAPLIPOINT", "Caplin Point", "Pharma", 2035.8, 2150.4],
  ["DEEPAKFERT", "Deepak Fertilisers", "Chemicals", 1448.7, 1521.0],
  ["COALINDIA", "Coal India", "Energy", 458.15, 449.3],
  ["NMDC", "NMDC", "Metals", 90.67, 95.1],
  ["CEMPRO", "Cement Products", "Construction", 943.3, 968.0],
  ["SOLARINDS", "Solar Industries", "Chemicals", 18479.0, 19200.0],
  ["PAGEIND", "Page Industries", "Textiles", 38305.0, 37600.0],
  ["BEL", "Bharat Electronics", "Capital Goods", 295.2, 314.0],
];
export async function getHoldings(): Promise<Holding[]> {
  // TODO(real): SELECT p.isin, s.nse_symbol, s.name, s.sector, p.entry_date,
  //   p.entry_price, p.shares, (latest prices_eod_adjusted.adj_close) AS current_price
  //   FROM paper_position p JOIN stocks s USING(isin) WHERE p.status = open
  const equity = 1_041_800;
  const holdings: Holding[] = RAW.map(([ticker, name, sector, entry, current]) => {
    const shares = 20000 / entry;
    const value = shares * current;
    return {
      isin: "INE" + ticker, ticker, name, sector, entryDate: INCEPTION,
      entryPrice: entry, currentPrice: current, shares,
      weightPct: (value / equity) * 100, pnlPct: (current / entry - 1) * 100,
    };
  });
  holdings.push({
    isin: "CASH", ticker: "CASH", name: "Cash (risk-off sleeve)", sector: "Cash",
    entryDate: INCEPTION, entryPrice: 0, currentPrice: 0, shares: 0,
    weightPct: (500_000 / equity) * 100, pnlPct: 0, isCash: true,
  });
  return holdings;
}

export async function getABReadout(): Promise<ABReadout> {
  // TODO(real): once a 2nd paper_account with score_source = agentic exists, compare curves
  return {
    hasAgentic: false, edgePct: null,
    note: "Agentic book goes live once the News / FMP / FII agents are wired. Until then "
      + "the record tests F+ on the mechanical composite (the validated signal).",
  };
}

export async function getScores(): Promise<ScoreRow[]> {
  // TODO(real): SELECT isin, composite_score, technical_score, fundamental_score,
  //   macro_score, sentiment_adj, signal_label FROM agent_score_snapshot
  //   WHERE computed_date = latest  JOIN stocks for ticker/name/sector
  const rows: [string, string, string, number, number, number][] = [
    ["ZYDUSLIFE", "Zydus Lifesciences", "Pharma", 78, 82, 74],
    ["EICHERMOT", "Eicher Motors", "Auto", 76, 80, 71],
    ["AJANTPHARM", "Ajanta Pharma", "Pharma", 74, 77, 70],
    ["SUZLON", "Suzlon Energy", "Capital Goods", 73, 88, 55],
    ["MARICO", "Marico", "FMCG", 71, 64, 80],
    ["DIVISLAB", "Divis Labs", "Pharma", 70, 72, 73],
    ["TRITURBINE", "Triveni Turbine", "Capital Goods", 69, 75, 66],
    ["PIDILITIND", "Pidilite", "Chemicals", 68, 66, 74],
    ["SOLARINDS", "Solar Industries", "Chemicals", 67, 79, 60],
    ["NMDC", "NMDC", "Metals", 64, 70, 58],
    ["COALINDIA", "Coal India", "Energy", 62, 60, 67],
    ["BEL", "Bharat Electronics", "Capital Goods", 61, 68, 59],
    ["TATAMOTORS", "Tata Motors", "Auto", 48, 44, 55],
    ["VEDL", "Vedanta", "Metals", 41, 38, 49],
    ["YESBANK", "Yes Bank", "Financials", 28, 22, 35],
  ];
  return rows.map(([ticker, name, sector, composite, momentum, quality]) => ({
    isin: "INE" + ticker, ticker, name, sector, composite, momentum, quality,
    news: null, sentiment: null,
    sectorScore: Math.round((momentum + quality) / 2 - 3),
    signal: composite >= 65 ? "bullish" : composite >= 45 ? "neutral" : "avoid",
  }));
}

function mockAgents(): AgentRun[] {
  // Time-driven so polling visibly ticks: the News agent progresses each poll.
  const runId = "run-2026-05-26";
  const t = Math.floor(Date.now() / 1000);
  const newsProg = Math.min(507, (t % 45) * 12 + 40);
  const mk = (
    agentName: string, group: AgentRun["group"], status: AgentRun["status"],
    headline: string, extra: Partial<AgentRun> = {},
  ): AgentRun => ({
    runId, agentName, group, status, headlineOutput: headline,
    progressCurrent: null, progressTotal: null,
    startedAt: null, finishedAt: null, durationMs: null, ...extra,
  });
  return [
    mk("Momentum", "selection", "done", "Scored 507 stocks, top RS = SUZLON", { durationMs: 4200 }),
    mk("Quality", "selection", "done", "312/507 passed the quality gate", { durationMs: 3100 }),
    mk("News", "selection", "running", "Scanning headlines",
      { progressCurrent: newsProg, progressTotal: 507 }),
    mk("Sentiment", "selection", "offline", "FinBERT idle", { offlineReason: "enable on cloud (torch)" }),
    mk("Fundamentals", "selection", "offline", "FMP not wired", { offlineReason: "FMP client pending (key valid)" }),
    mk("Sector", "market", "done", "Cap Goods + Pharma leading", { durationMs: 1800 }),
    mk("FII / DII", "market", "done", "Net FII -2,340 Cr", { durationMs: 900 }),
    mk("Macro", "market", "done", "Regime: RISK-OFF (below 200-DMA)", { durationMs: 700 }),
    mk("Risk", "market", "done", "No single-name > 4% breach", { durationMs: 1100 }),
    mk("Breadth", "market", "done", "38% above 200-DMA", { durationMs: 800 }),
    mk("Ranking", "meta", "done", "Composite ranked 365 scoreable", { durationMs: 2600 }),
    mk("Meta-Auditor", "meta", "waiting", "Waiting on News to finish"),
  ];
}
export async function getAgentBoard(): Promise<AgentBoard> {
  // TODO(real): SELECT * FROM agent_run_log WHERE run_id = latest ORDER BY agent_name
  const agents = mockAgents();
  return {
    runId: "run-2026-05-26", lastRun: new Date().toISOString(),
    inProgress: agents.some((a) => a.status === "running"), agents,
  };
}

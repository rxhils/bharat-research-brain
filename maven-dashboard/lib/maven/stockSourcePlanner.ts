import type { StockSourcePlan, StockDepth, AnswerType } from "./types";
import { getExpectedLatestQuarter, getCurrentIndianFiscalYear, formatFiscalPeriod } from "./reportingPeriods";

// Decides research depth + a source budget so Maven doesn't fetch 25 pages for a one-line profile
// query, but does go deep on explicit "full research" requests. Query strings target official
// domains first (resolved by sourceSearch's ranker) then reputable media.

// Kept in sync with reportModeDetector.ts's trigger phrases so a Deep Research Report always
// gets the deep (22-source) budget, regardless of which detector's wording happened to match.
const DEEP = /\b(full research|full report|full view|in detail|detailed|deep(?:ly|\s+dive)?|analy[sz]e\b.*\b(fully|detail)|risks?\s+in|complete (view|picture|analysis|report)|everything about|thesis on|investment thesis|business breakdown|research note|institutional[- ]?style report)\b/i;
const LIGHT = /^\s*(what is|who is|explain|profile of|tell me about)\b/i;

export function stockDepthFor(query: string, answerType: AnswerType): StockDepth {
  if (DEEP.test(query)) return "deep";
  if (answerType === "stock_comparison") return "standard";
  if (LIGHT.test(query) && query.trim().split(/\s+/).length <= 5) return "light";
  return "standard";
}

const BUDGET: Record<StockDepth, number> = { light: 6, standard: 12, deep: 22 };

export function planStockSources(query: string, companyName: string, answerType: AnswerType): StockSourcePlan {
  const depth = stockDepthFor(query, answerType);
  const name = companyName || query.trim();
  // latest-period-labeled queries so retrieval targets the CURRENT reporting cycle, not old FYs
  const expQ = formatFiscalPeriod(getExpectedLatestQuarter());
  const curFY = `FY${getCurrentIndianFiscalYear()}`;

  const officialQueries = [
    `site:nseindia.com ${name} announcement`,
    `site:bseindia.com ${name} corporate announcement`,
  ];
  const searchQueries = [
    `${name} stock news today India why moving`,
    `${name} latest quarterly results ${expQ}`,
  ];
  if (/market share/i.test(query)) searchQueries.push(`${name} market share latest ${curFY}`, `${name} investor presentation market share`);
  const requiredSources = ["announcements", "price", "sector"];
  const chartNeeds = ["stock_line", "index_compare"];

  if (depth !== "light") {
    officialQueries.push(`${name} investor relations results ${curFY}`, `${name} shareholding pattern NSE BSE latest`);
    searchQueries.push(`${name} share price analysis Moneycontrol`, `${name} ${expQ} earnings BusinessLine Mint`);
    requiredSources.push("results", "shareholding", "fundamentals", "news");
    chartNeeds.push("valuation");
  }
  if (depth === "deep") {
    officialQueries.push(`${name} annual report investor presentation latest`, `${name} corporate actions board meeting NSE`);
    searchQueries.push(`${name} credit rating outlook`, `${name} peer comparison sector India`, `${name} latest management commentary concall`);
    requiredSources.push("annual_report", "presentation", "peers", "macro");
    chartNeeds.push("peer_table", "shareholding_table");
  }

  return { depth, sourceBudget: BUDGET[depth], requiredSources, searchQueries, officialQueries, chartNeeds };
}

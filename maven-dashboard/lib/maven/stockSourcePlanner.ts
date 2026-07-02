import type { StockSourcePlan, StockDepth, AnswerType } from "./types";

// Decides research depth + a source budget so Maven doesn't fetch 25 pages for a one-line profile
// query, but does go deep on explicit "full research" requests. Query strings target official
// domains first (resolved by sourceSearch's ranker) then reputable media.

const DEEP = /\b(full research|in detail|detailed|deep(?:\s+dive)?|analy[sz]e\b.*\b(fully|detail)|risks?\s+in|complete (view|picture|analysis)|everything about|thesis on)\b/i;
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

  const officialQueries = [
    `site:nseindia.com ${name} announcement`,
    `site:bseindia.com ${name} corporate announcement`,
  ];
  const searchQueries = [
    `${name} stock news today India why moving`,
    `${name} latest results India`,
  ];
  const requiredSources = ["announcements", "price", "sector"];
  const chartNeeds = ["stock_line", "index_compare"];

  if (depth !== "light") {
    officialQueries.push(`${name} investor relations results`, `${name} shareholding pattern NSE BSE`);
    searchQueries.push(`${name} share price analysis Moneycontrol`, `${name} quarterly earnings BusinessLine Mint`);
    requiredSources.push("results", "shareholding", "fundamentals", "news");
    chartNeeds.push("valuation");
  }
  if (depth === "deep") {
    officialQueries.push(`${name} annual report investor presentation`, `${name} corporate actions board meeting NSE`);
    searchQueries.push(`${name} credit rating outlook`, `${name} peer comparison sector India`, `${name} management commentary concall`);
    requiredSources.push("annual_report", "presentation", "peers", "macro");
    chartNeeds.push("peer_table", "shareholding_table");
  }

  return { depth, sourceBudget: BUDGET[depth], requiredSources, searchQueries, officialQueries, chartNeeds };
}

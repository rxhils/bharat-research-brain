import type { Intent, ResearchPlan } from "./types";

const ENTITIES: Record<string, string> = {
  banks: "Banks", bank: "Banks", financials: "Banks", it: "IT", pharma: "Pharma", auto: "Auto",
  fmcg: "FMCG", metal: "Metal", realty: "Realty", energy: "Energy", crude: "crude oil", oil: "crude oil",
  rupee: "rupee", nifty: "Nifty 50", sensex: "Sensex", "bank nifty": "Bank Nifty", midcap: "Midcap",
  smallcap: "Smallcap", rbi: "RBI policy", fii: "FII flows", dii: "DII flows", inflation: "inflation",
};

export function extractTopic(query: string, intent: Intent): string {
  const s = (query || "").toLowerCase();
  for (const k of Object.keys(ENTITIES)) { if (new RegExp("\\b" + k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\b").test(s)) return ENTITIES[k]; }
  if (intent === "market_summary") return "Indian market today";
  if (intent === "index_movement") return "Nifty 50";
  return query.trim().slice(0, 60);
}

export function planResearch(query: string, intent: Intent): ResearchPlan {
  const topic = extractTopic(query, intent);
  const mk = (requiredData: string[], requiredCharts: string[], searchQueries: string[], requiresLiveData = true): ResearchPlan =>
    ({ intent, topic, requiresLiveData, requiredData, searchQueries, requiredCharts });

  switch (intent) {
    case "market_summary":
      return mk(
        ["indices", "sectors", "fiidii", "crude", "usdinr", "gsec"],
        ["index_line", "sector_bar", "fiidii_bar"],
        [`Indian stock market today ${topic}`, "Nifty Sensex close today reasons", "FII DII activity today India"],
      );
    case "index_movement":
      return mk(
        ["indices", "sectors", "gsec", "fiidii"],
        ["index_line", "sector_bar"],
        [`why is ${topic} moving today`, `${topic} today India news`],
      );
    case "sector_impact":
      return mk(
        ["sectors", "indices", "crude", "usdinr", "gsec", "fiidii"],
        ["sector_bar"],
        [`${topic} India market today`, `${topic} impact Indian stocks`],
      );
    case "stock_comparison":
      return mk(
        ["stocks", "sectors"],
        ["stock_compare", "valuation"],
        [`${topic} comparison India`, `${topic} latest quarterly results`],
      );
    case "macro_impact":
      return mk(
        ["crude", "usdinr", "gsec"],
        ["macro_line"],
        [`${topic} India impact markets`, `${topic} latest data India`],
      );
    case "term_explanation":
      return mk([], [], [`${topic} meaning Indian markets`], false);
    default:
      return mk([], [], [], false);
  }
}
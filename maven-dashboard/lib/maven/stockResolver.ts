import type { ResolvedStock } from "./types";

type Def = { name: string; symbol: string; sector: string; aliases: string[] };

// Common Indian large/mid caps -> NSE symbols + sector. Extend freely; aliases are word-boundary matched.
const STOCKS: Def[] = [
  { name: "Reliance Industries", symbol: "RELIANCE", sector: "Energy", aliases: ["reliance", "ril"] },
  { name: "HDFC Bank", symbol: "HDFCBANK", sector: "Banks", aliases: ["hdfc bank", "hdfcbank", "hdfc"] },
  { name: "ICICI Bank", symbol: "ICICIBANK", sector: "Banks", aliases: ["icici bank", "icicibank", "icici"] },
  { name: "State Bank of India", symbol: "SBIN", sector: "Banks", aliases: ["sbi", "state bank of india", "state bank"] },
  { name: "Axis Bank", symbol: "AXISBANK", sector: "Banks", aliases: ["axis bank", "axisbank"] },
  { name: "Kotak Mahindra Bank", symbol: "KOTAKBANK", sector: "Banks", aliases: ["kotak mahindra", "kotak bank", "kotak"] },
  { name: "Bajaj Finance", symbol: "BAJFINANCE", sector: "Financials", aliases: ["bajaj finance", "bajfinance"] },
  { name: "Tata Motors", symbol: "TATAMOTORS", sector: "Auto", aliases: ["tata motors", "tatamotors", "jlr"] },
  { name: "Maruti Suzuki", symbol: "MARUTI", sector: "Auto", aliases: ["maruti suzuki", "maruti"] },
  { name: "Infosys", symbol: "INFY", sector: "IT", aliases: ["infosys", "infy"] },
  { name: "Tata Consultancy Services", symbol: "TCS", sector: "IT", aliases: ["tcs", "tata consultancy"] },
  { name: "Wipro", symbol: "WIPRO", sector: "IT", aliases: ["wipro"] },
  { name: "HCL Technologies", symbol: "HCLTECH", sector: "IT", aliases: ["hcl technologies", "hcltech", "hcl tech"] },
  { name: "Zomato (Eternal)", symbol: "ZOMATO", sector: "Internet", aliases: ["zomato", "eternal"] },
  { name: "Paytm (One97)", symbol: "PAYTM", sector: "Internet", aliases: ["paytm", "one97"] },
  { name: "Bharat Electronics", symbol: "BEL", sector: "Defence", aliases: ["bharat electronics", "\\bbel\\b"] },
  { name: "Hindustan Aeronautics", symbol: "HAL", sector: "Defence", aliases: ["hindustan aeronautics", "\\bhal\\b"] },
  { name: "Coal India", symbol: "COALINDIA", sector: "Energy", aliases: ["coal india", "coalindia"] },
  { name: "Oil and Natural Gas Corp", symbol: "ONGC", sector: "Energy", aliases: ["ongc", "oil and natural gas"] },
  { name: "Hindustan Zinc", symbol: "HINDZINC", sector: "Metal", aliases: ["hindustan zinc", "hindzinc"] },
  { name: "Tata Steel", symbol: "TATASTEEL", sector: "Metal", aliases: ["tata steel", "tatasteel"] },
  { name: "ITC", symbol: "ITC", sector: "FMCG", aliases: ["\\bitc\\b"] },
  { name: "Larsen & Toubro", symbol: "LT", sector: "Infra", aliases: ["larsen & toubro", "larsen", "l&t"] },
  { name: "Bharti Airtel", symbol: "BHARTIARTL", sector: "Telecom", aliases: ["bharti airtel", "airtel", "bharti"] },
  { name: "Sun Pharma", symbol: "SUNPHARMA", sector: "Pharma", aliases: ["sun pharma", "sunpharma"] },
  { name: "Cipla", symbol: "CIPLA", sector: "Pharma", aliases: ["cipla"] },
  { name: "Adani Enterprises", symbol: "ADANIENT", sector: "Infra", aliases: ["adani enterprises", "adani ent", "adani"] },
];

function matches(alias: string, s: string): boolean {
  const body = alias.startsWith("\\b") ? alias : "\\b" + alias.replace(/[.*+?^${}()|[\]]/g, "\\$&") + "\\b";
  return new RegExp(body).test(s);
}

export function extractSymbols(query: string): string[] {
  const s = (query || "").toLowerCase(); const out: string[] = [];
  for (const d of STOCKS) if (d.aliases.some((a) => matches(a, s)) && !out.includes(d.symbol)) out.push(d.symbol);
  return out.slice(0, 3);
}

export function resolveStock(query: string): ResolvedStock | null {
  const s = (query || "").toLowerCase();
  let best: { d: Def; len: number } | null = null;
  for (const d of STOCKS) for (const a of d.aliases) if (matches(a, s)) { const len = a.replace(/\\b/g, "").length; if (!best || len > best.len) best = { d, len }; }
  if (!best) return null;
  const d = best.d;
  return { companyName: d.name, symbol: d.symbol + ".NS", exchange: "NSE", sector: d.sector, confidence: best.len >= 4 ? "high" : "medium" };
}

export function sectorGroup(sector: string): "banks" | "energy" | "exporter" | "other" {
  const x = (sector || "").toLowerCase();
  if (x === "banks" || x === "financials") return "banks";
  if (x === "energy") return "energy";
  if (x === "it" || x === "pharma") return "exporter";
  return "other";
}
export function nameForSymbol(symbol: string): string | undefined {
  const sym = symbol.replace(/\.ns$/i, "").toUpperCase();
  return STOCKS.find((d) => d.symbol === sym)?.name;
}

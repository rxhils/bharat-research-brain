import type { Quote, SectorPerf, Flows } from "./types";

// Live India market data via Yahoo Finance (yfinance is allowlisted; NO NSE scraping).
// Architecture is real-API ready: each tool returns typed data or null (never fabricates).
const YF = "https://query1.finance.yahoo.com/v8/finance/chart/";
const UA = "Mozilla/5.0 (compatible; MavenResearch/1.0)";

async function yq(symbol: string, label: string): Promise<Quote> {
  try {
    const r = await fetch(YF + encodeURIComponent(symbol) + "?interval=15m&range=1d", { headers: { "User-Agent": UA }, next: { revalidate: 45 } });
    if (!r.ok) throw new Error(String(r.status));
    const j: any = await r.json();
    const res = j?.chart?.result?.[0];
    const m = res?.meta ?? {};
    const price = typeof m.regularMarketPrice === "number" ? m.regularMarketPrice : null;
    const prev = typeof m.chartPreviousClose === "number" ? m.chartPreviousClose : (typeof m.previousClose === "number" ? m.previousClose : null);
    const closes: number[] = (res?.indicators?.quote?.[0]?.close ?? []).filter((x: number | null): x is number => typeof x === "number");
    return { label, symbol, price, changePct: price != null && prev ? ((price - prev) / prev) * 100 : null, spark: closes.slice(-40) };
  } catch {
    return { label, symbol, price: null, changePct: null };
  }
}

const INDICES: [string, string][] = [["^NSEI", "Nifty 50"], ["^BSESN", "Sensex"], ["^NSEBANK", "Bank Nifty"], ["^CNXMIDCAP", "Nifty Midcap"], ["^CNXSC", "Nifty Smallcap"]];
const SECTORS: [string, string][] = [["^NSEBANK", "Banks"], ["^CNXIT", "IT"], ["^CNXAUTO", "Auto"], ["^CNXPHARMA", "Pharma"], ["^CNXFMCG", "FMCG"], ["^CNXENERGY", "Energy"], ["^CNXMETAL", "Metal"], ["^CNXREALTY", "Realty"]];

export async function getIndexPerformance(index?: string): Promise<Quote[]> {
  const set = index ? INDICES.filter(([, l]) => l.toLowerCase().includes(index.toLowerCase())) : INDICES;
  return Promise.all((set.length ? set : INDICES).map(([s, l]) => yq(s, l)));
}

export async function getSectorPerformance(): Promise<SectorPerf[]> {
  const qs = await Promise.all(SECTORS.map(([s, l]) => yq(s, l)));
  return qs.filter((q) => q.changePct != null).map((q) => ({ name: q.label, changePct: q.changePct as number })).sort((a, b) => b.changePct - a.changePct);
}

export async function getStockPrice(symbol: string): Promise<Quote> {
  const sym = symbol.includes(".") ? symbol : symbol.toUpperCase() + ".NS";
  return yq(sym, symbol.toUpperCase());
}

export async function getCrudePrice(): Promise<Quote> { return yq("BZ=F", "Brent crude"); }
export async function getUSDINR(): Promise<Quote> { return yq("INR=X", "USD / INR"); }

// India 10Y G-Sec yield is not reliably on Yahoo; return null + a clear marker (wire a real
// source: RBI / NSE bond data) - never invent it.
export async function getGSecYield(): Promise<{ yieldPct: number | null; asOf: string } | null> {
  return { yieldPct: null, asOf: "unavailable" };
}

// FII/DII cash flows are EOD (NSDL/exchange). No free live feed wired yet -> null + marker.
export async function getFIIDIIFlows(): Promise<Flows> {
  return { fiiCr: null, diiCr: null, asOf: "EOD source not wired" };
}

export async function getLatestNews(_topic: string): Promise<[]> { return []; } // handled by sourceSearch
export async function getCompanySnapshot(symbol: string): Promise<Quote> { return getStockPrice(symbol); }
export async function getMacroSnapshot(_topic: string): Promise<{ crude: Quote; usdinr: Quote }> {
  const [crude, usdinr] = await Promise.all([getCrudePrice(), getUSDINR()]);
  return { crude, usdinr };
}
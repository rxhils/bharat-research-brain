import type { MarketSnapshot, Quote, Sector } from "./types";

// Live India market data via Yahoo Finance (yfinance is on the project allowlist; NO NSE scraping).
// Server-only. Falls back to clearly-labelled sample data if egress is unavailable.
const YF = "https://query1.finance.yahoo.com/v8/finance/chart/";
const UA = "Mozilla/5.0 (compatible; MavenResearch/1.0)";

const INDEX_DEFS: { symbol: string; label: string }[] = [
  { symbol: "^NSEI", label: "Nifty 50" },
  { symbol: "^BSESN", label: "Sensex" },
  { symbol: "^NSEBANK", label: "Bank Nifty" },
  { symbol: "^CNXMIDCAP", label: "Nifty Midcap" },
  { symbol: "^CNXSC", label: "Nifty Smallcap" },
  { symbol: "^INDIAVIX", label: "India VIX" },
  { symbol: "INR=X", label: "USD / INR" },
];

const SECTOR_DEFS: { symbol: string; name: string }[] = [
  { symbol: "^NSEBANK", name: "Banks" },
  { symbol: "^CNXIT", name: "IT" },
  { symbol: "^CNXAUTO", name: "Auto" },
  { symbol: "^CNXPHARMA", name: "Pharma" },
  { symbol: "^CNXFMCG", name: "FMCG" },
  { symbol: "^CNXENERGY", name: "Energy" },
  { symbol: "^CNXMETAL", name: "Metal" },
  { symbol: "^CNXREALTY", name: "Realty" },
];

async function chart(symbol: string): Promise<{ price: number | null; prev: number | null; closes: number[] }> {
  const r = await fetch(YF + encodeURIComponent(symbol) + "?interval=15m&range=1d", {
    headers: { "User-Agent": UA },
    next: { revalidate: 45 },
  });
  if (!r.ok) throw new Error(symbol + " " + r.status);
  const j: any = await r.json();
  const res = j?.chart?.result?.[0];
  const meta = res?.meta ?? {};
  const price = typeof meta.regularMarketPrice === "number" ? meta.regularMarketPrice : null;
  const prev =
    typeof meta.chartPreviousClose === "number" ? meta.chartPreviousClose
    : typeof meta.previousClose === "number" ? meta.previousClose
    : null;
  const closes: number[] = (res?.indicators?.quote?.[0]?.close ?? []).filter(
    (x: number | null): x is number => typeof x === "number",
  );
  return { price, prev, closes };
}

async function quoteOf(symbol: string, label: string): Promise<Quote> {
  try {
    const { price, prev, closes } = await chart(symbol);
    const changePct = price != null && prev ? ((price - prev) / prev) * 100 : null;
    return { symbol, label, price, changePct, spark: closes.slice(-48) };
  } catch {
    return { symbol, label, price: null, changePct: null };
  }
}

const SAMPLE: MarketSnapshot = {
  live: false,
  asOf: "",
  source: "Sample data (live feed unavailable here)",
  indices: [
    { symbol: "^NSEI", label: "Nifty 50", price: 24218.6, changePct: 0.62 },
    { symbol: "^BSESN", label: "Sensex", price: 79480.2, changePct: 0.55 },
    { symbol: "^NSEBANK", label: "Bank Nifty", price: 52140.3, changePct: 0.94 },
    { symbol: "^CNXMIDCAP", label: "Nifty Midcap", price: 58210.0, changePct: 0.31 },
    { symbol: "^CNXSC", label: "Nifty Smallcap", price: 18120.4, changePct: -0.12 },
    { symbol: "^INDIAVIX", label: "India VIX", price: 13.4, changePct: -3.1 },
    { symbol: "INR=X", label: "USD / INR", price: 83.42, changePct: -0.08 },
  ],
  sectors: [
    { name: "Banks", changePct: 0.94 },
    { name: "IT", changePct: 0.7 },
    { name: "Energy", changePct: 0.5 },
    { name: "Auto", changePct: 0.28 },
    { name: "Pharma", changePct: 0.1 },
    { name: "FMCG", changePct: -0.15 },
    { name: "Metal", changePct: -0.42 },
    { name: "Realty", changePct: -0.6 },
  ],
  pulse: {
    breadthAdv: 31,
    breadthDec: 19,
    flows: { fiiCr: 1240, diiCr: 880, asOf: "prev session (EOD)" },
    topSectors: [],
    themes: ["Bank liquidity", "Softer crude", "Defence capex", "Railways"],
    headlines: [
      { title: "Financials lead as bond yields ease", source: "Mint", time: "today" },
      { title: "Crude slips, OMCs in focus", source: "BusinessLine", time: "today" },
    ],
  },
};

export async function getSnapshot(): Promise<MarketSnapshot> {
  const asOf = new Date().toISOString();
  const indices = await Promise.all(INDEX_DEFS.map((d) => quoteOf(d.symbol, d.label)));
  const live = indices.some((q) => q.price != null);
  if (!live) return { ...SAMPLE, asOf };

  const sec = await Promise.all(
    SECTOR_DEFS.map(async (d) => {
      try {
        const { price, prev } = await chart(d.symbol);
        return price != null && prev ? { name: d.name, changePct: ((price - prev) / prev) * 100 } : null;
      } catch {
        return null;
      }
    }),
  );
  const sectors: Sector[] = sec
    .filter((s): s is Sector => s != null)
    .sort((a, b) => b.changePct - a.changePct);

  return {
    live: true,
    asOf,
    source: "Yahoo Finance (delayed)",
    indices,
    sectors: sectors.length ? sectors : SAMPLE.sectors,
    pulse: { ...SAMPLE.pulse, topSectors: (sectors.length ? sectors : SAMPLE.sectors).slice(0, 3) },
  };
}
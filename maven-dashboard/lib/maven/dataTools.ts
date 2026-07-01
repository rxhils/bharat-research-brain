import type { Quote, SectorPerf, FiiDiiFlows, GSecYield, MacroSnapshot, MarketDataPoint, CompanyAnnouncements, Announcement, CompanySnapshot } from "./types";
import { searchSources } from "./sourceSearch";

// Live India market data via Yahoo (yfinance allowlisted; NO NSE scraping) + Tavily-retrieved
// fallbacks for feeds without a stable free live source (FII/DII, G-Sec, macro). Never fabricates:
// a value appears only when found in a cited source, else null + a clean limitation.
const YF = "https://query1.finance.yahoo.com/v8/finance/chart/";
const UA = "Mozilla/5.0 (compatible; MavenResearch/1.0)";

// ---- simple in-memory TTL cache --------------------------------------------
const _cache = new Map<string, { t: number; ttl: number; v: unknown }>();
async function cached<T>(key: string, ttlMs: number, fn: () => Promise<T>): Promise<T> {
  const now = Date.now();
  const hit = _cache.get(key);
  if (hit && now - hit.t < hit.ttl) return hit.v as T;
  const v = await fn();
  _cache.set(key, { t: now, ttl: ttlMs, v });
  return v;
}

const round2 = (n: number) => Math.round(n * 100) / 100;
function pctIn(text: string, lo: number, hi: number): number | null {
  const re = /(\d{1,2}(?:\.\d{1,2})?)\s*%/g; let m: RegExpExecArray | null;
  while ((m = re.exec(text || "")) !== null) { const v = parseFloat(m[1]); if (v >= lo && v <= hi) return v; }
  return null;
}
function mdp(key: string, label: string, value: number | string | null, unit: string, changePct: number | null, source: string, freshness: MarketDataPoint["freshness"], confidence: MarketDataPoint["confidence"], sourceUrl?: string, limitation?: string): MarketDataPoint {
  return { key, label, value, unit: unit || undefined, changePct: changePct ?? null, source, sourceUrl, freshness, confidence, limitation };
}

// ---- live Yahoo quotes ------------------------------------------------------
async function yq(symbol: string, label: string): Promise<Quote> {
  try {
    const r = await fetch(YF + encodeURIComponent(symbol) + "?interval=15m&range=1d", { headers: { "User-Agent": UA }, next: { revalidate: 120 } });
    if (!r.ok) throw new Error(String(r.status));
    const j: any = await r.json();
    const res = j?.chart?.result?.[0]; const m = res?.meta ?? {};
    const price = typeof m.regularMarketPrice === "number" ? m.regularMarketPrice : null;
    const prev = typeof m.chartPreviousClose === "number" ? m.chartPreviousClose : (typeof m.previousClose === "number" ? m.previousClose : null);
    const closes: number[] = (res?.indicators?.quote?.[0]?.close ?? []).filter((x: number | null): x is number => typeof x === "number");
    return { label, symbol, price, changePct: price != null && prev ? ((price - prev) / prev) * 100 : null, spark: closes.slice(-40) };
  } catch { return { label, symbol, price: null, changePct: null }; }
}

const INDICES: [string, string][] = [["^NSEI", "Nifty 50"], ["^BSESN", "Sensex"], ["^NSEBANK", "Bank Nifty"], ["^CNXMIDCAP", "Nifty Midcap"], ["^CNXSC", "Nifty Smallcap"]];
const SECTORS: [string, string][] = [["^NSEBANK", "Banks"], ["^CNXIT", "IT"], ["^CNXAUTO", "Auto"], ["^CNXPHARMA", "Pharma"], ["^CNXFMCG", "FMCG"], ["^CNXENERGY", "Energy"], ["^CNXMETAL", "Metal"], ["^CNXREALTY", "Realty"]];

export async function getIndexPerformance(index?: string): Promise<Quote[]> {
  return cached("indices:" + (index ?? "all"), 120_000, async () => {
    const set = index ? INDICES.filter(([, l]) => l.toLowerCase().includes(index.toLowerCase())) : INDICES;
    return Promise.all((set.length ? set : INDICES).map(([s, l]) => yq(s, l)));
  });
}
export async function getSectorPerformance(): Promise<SectorPerf[]> {
  return cached("sectors", 240_000, async () => {
    const qs = await Promise.all(SECTORS.map(([s, l]) => yq(s, l)));
    return qs.filter((q) => q.changePct != null).map((q) => ({ name: q.label, changePct: q.changePct as number })).sort((a, b) => b.changePct - a.changePct);
  });
}
export async function getStockPrice(symbol: string): Promise<Quote> {
  const sym = symbol.includes(".") ? symbol : symbol.toUpperCase() + ".NS";
  return cached("price:" + sym, 120_000, () => yq(sym, symbol.toUpperCase()));
}
export async function getCrudePrice(): Promise<Quote> { return cached("crude", 180_000, () => yq("BZ=F", "Brent crude")); }
export async function getUSDINR(): Promise<Quote> { return cached("usdinr", 120_000, () => yq("INR=X", "USD / INR")); }

// ---- 10Y G-Sec yield (retrieved fallback) ----------------------------------
export async function getGSecYield(): Promise<GSecYield> {
  return cached("gsec", 20 * 60_000, async () => {
    const res = await searchSources(["India 10 year G-Sec government bond yield today", "India 10Y benchmark bond yield latest"]);
    let y: number | null = null; let src = res[0];
    for (const r of res.slice(0, 4)) { const v = pctIn(r.snippet || "", 5, 9); if (v != null) { y = v; src = r; break; } }
    if (y != null && src) return { yield10Y: y, changeBps: null, date: src.published, source: src.source, sourceUrl: src.url, freshness: "latest_available", confidence: "retrieved", limitation: "10Y G-Sec change (bps) unavailable; level from latest retrieved source." };
    return { yield10Y: null, source: "Maven analysis", freshness: "unavailable", confidence: "unavailable", limitation: "10Y G-Sec yield unavailable from current sources." };
  });
}

// ---- FII/DII flows (retrieved context fallback) ----------------------------
export async function getFIIDIIFlows(): Promise<FiiDiiFlows> {
  return cached("fiidii", 45 * 60_000, async () => {
    const res = await searchSources(["FII DII activity today India cash market net buy sell crore", "FPI DII provisional cash data NSE today"]);
    const top = res[0];
    if (top) return { fiiCashNet: null, diiCashNet: null, context: top.snippet, date: top.published, source: top.source, sourceUrl: top.url, freshness: "latest_available", confidence: "retrieved", limitation: "Live FII/DII feed unavailable; using latest retrieved institutional-flow context." };
    return { fiiCashNet: null, diiCashNet: null, source: "Maven analysis", freshness: "unavailable", confidence: "unavailable", limitation: "FII/DII flow data unavailable from current sources." };
  });
}

// ---- India macro snapshot ---------------------------------------------------
export async function getIndiaMacroSnapshot(): Promise<MacroSnapshot> {
  const [crude, usdinr] = await Promise.all([getCrudePrice(), getUSDINR()]);
  const points: MarketDataPoint[] = [];
  if (crude.price != null) points.push(mdp("crude", "Brent crude", round2(crude.price), "USD/bbl", crude.changePct, "Yahoo Finance", "live", "retrieved"));
  if (usdinr.price != null) points.push(mdp("usdinr", "USD/INR", round2(usdinr.price), "", usdinr.changePct, "Yahoo Finance", "live", "retrieved"));

  const retrieved = await cached("macro_in", 12 * 3600_000, async () => {
    const out: MarketDataPoint[] = [];
    const defs: [string, string, string, number, number][] = [
      ["cpi", "CPI inflation", "India CPI inflation latest rate percent", 0, 20],
      ["repo", "RBI repo rate", "India RBI repo rate current percent", 3, 10],
    ];
    for (const [key, label, q, lo, hi] of defs) {
      const rs = await searchSources([q]); const r = rs[0];
      if (!r) continue;
      const v = pctIn(r.snippet || "", lo, hi);
      out.push(mdp(key, label, v, "%", null, r.source, "latest_available", "retrieved", r.url, v == null ? "Latest figure not parsed; see source." : undefined));
    }
    return out;
  });
  points.push(...retrieved);

  const gsec = await getGSecYield();
  if (gsec.yield10Y != null) points.push(mdp("gsec10y", "10Y G-Sec", gsec.yield10Y, "%", null, gsec.source, gsec.freshness, gsec.confidence, gsec.sourceUrl));

  const limitation = points.some((p) => p.value == null) ? "Some macro indicators are latest-available from retrieved sources, not live." : undefined;
  return { points, limitation };
}

// ---- company announcements (retrieved) -------------------------------------
export async function getCompanyAnnouncements(symbol: string): Promise<CompanyAnnouncements> {
  return cached("ann:" + symbol, 30 * 60_000, async () => {
    const res = await searchSources([symbol + " NSE BSE announcement results corporate filing", symbol + " stock news today India"]);
    if (!res.length) return { symbol: symbol.toUpperCase(), announcements: [], limitation: "No recent announcements found from current sources." };
    const announcements: Announcement[] = res.slice(0, 5).map((r) => ({ title: r.title, date: r.published, source: r.source, sourceUrl: r.url, type: "news_fallback", snippet: r.snippet, confidence: "retrieved" }));
    return { symbol: symbol.toUpperCase(), announcements };
  });
}

// ---- company snapshot (Yahoo quoteSummary, graceful) -----------------------
export async function getCompanySnapshot(symbol: string): Promise<CompanySnapshot> {
  const sym = symbol.includes(".") ? symbol : symbol.toUpperCase() + ".NS";
  return cached("snap:" + sym, 120_000, async () => {
    const q = await getStockPrice(symbol);
    const points: MarketDataPoint[] = [];
    if (q.price != null) points.push(mdp("price", "Price", round2(q.price), "₹", q.changePct, "Yahoo Finance", "live", "retrieved"));
    let sector: string | undefined;
    try {
      const r = await fetch("https://query2.finance.yahoo.com/v10/finance/quoteSummary/" + encodeURIComponent(sym) + "?modules=summaryDetail,defaultKeyStatistics,financialData,assetProfile,price", { headers: { "User-Agent": UA }, next: { revalidate: 1800 } });
      if (r.ok) {
        const j: any = await r.json(); const res = j?.quoteSummary?.result?.[0];
        const sd = res?.summaryDetail, ks = res?.defaultKeyStatistics, fd = res?.financialData, ap = res?.assetProfile, pr = res?.price;
        sector = ap?.sector;
        const mc = pr?.marketCap?.raw ?? sd?.marketCap?.raw; if (typeof mc === "number") points.push(mdp("mktcap", "Market cap", Math.round(mc / 1e7), "₹ Cr", null, "Yahoo Finance", "latest_available", "retrieved"));
        const pe = sd?.trailingPE?.raw ?? ks?.trailingPE?.raw; if (typeof pe === "number") points.push(mdp("pe", "P/E", round2(pe), "", null, "Yahoo Finance", "latest_available", "retrieved"));
        const pb = ks?.priceToBook?.raw; if (typeof pb === "number") points.push(mdp("pb", "P/B", round2(pb), "", null, "Yahoo Finance", "latest_available", "retrieved"));
        const roe = fd?.returnOnEquity?.raw; if (typeof roe === "number") points.push(mdp("roe", "ROE", round2(roe * 100), "%", null, "Yahoo Finance", "latest_available", "retrieved"));
        const dy = sd?.dividendYield?.raw; if (typeof dy === "number") points.push(mdp("divyield", "Dividend yield", round2(dy * 100), "%", null, "Yahoo Finance", "latest_available", "retrieved"));
        const hi = sd?.fiftyTwoWeekHigh?.raw, lo = sd?.fiftyTwoWeekLow?.raw; if (typeof hi === "number" && typeof lo === "number") points.push(mdp("range52", "52-wk range", round2(lo) + " - " + round2(hi), "₹", null, "Yahoo Finance", "latest_available", "retrieved"));
      }
    } catch { /* graceful: price-only */ }
    const limitation = points.length <= 1 ? "Detailed fundamentals unavailable from current source; price shown." : undefined;
    return { symbol: symbol.toUpperCase(), sector, points, limitation };
  });
}
import type { Quote, SectorPerf, FiiDiiFlows, GSecYield, MacroSnapshot, MarketDataPoint, CompanyAnnouncements, Announcement, CompanySnapshot, ResultContext, ShareholdingContext } from "./types";
import { searchSources } from "./sourceSearch";

// Live Yahoo + Tavily-retrieved fallbacks. Never fabricates: a value appears only when found in
// a cited source, else null + a clean user-facing limitation.
const YF = "https://query1.finance.yahoo.com/v8/finance/chart/";
const QS = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/";
const UA = "Mozilla/5.0 (compatible; MavenResearch/1.0)";

const _cache = new Map<string, { t: number; ttl: number; v: unknown }>();
async function cached<T>(key: string, ttlMs: number, fn: () => Promise<T>): Promise<T> {
  const now = Date.now(); const hit = _cache.get(key);
  if (hit && now - hit.t < hit.ttl) return hit.v as T;
  const v = await fn(); _cache.set(key, { t: now, ttl: ttlMs, v }); return v;
}

const round2 = (n: number) => Math.round(n * 100) / 100;
const num = (x: unknown): number | null => (typeof x === "number" && isFinite(x) ? x : null);
const r2 = (x: unknown): number | null => { const n = num(x); return n == null ? null : round2(n); };
const mulPct = (x: unknown): number | null => { const n = num(x); return n == null ? null : round2(n * 100); };

function pctIn(text: string, lo: number, hi: number): number | null {
  const re = /(\d{1,2}(?:\.\d{1,2})?)\s*%/g; let m: RegExpExecArray | null;
  while ((m = re.exec(text || "")) !== null) { const v = parseFloat(m[1]); if (v >= lo && v <= hi) return v; }
  return null;
}
function numNear(text: string, label: RegExp, lo: number, hi: number): number | null {
  const m = (text || "").match(new RegExp(label.source + "[^\\d]{0,16}(\\d{1,4}(?:\\.\\d{1,2})?)", "i"));
  if (m) { const v = parseFloat(m[1]); if (v >= lo && v <= hi) return v; } return null;
}
function pctNear(text: string, label: RegExp, lo: number, hi: number): number | null {
  const m = (text || "").match(new RegExp(label.source + "[^\\d%]{0,22}(-?\\d{1,3}(?:\\.\\d{1,2})?)\\s*%", "i"));
  if (m) { const v = parseFloat(m[1]); if (v >= lo && v <= hi) return v; } return null;
}
function mdp(key: string, label: string, value: number | string | null, unit: string, changePct: number | null, source: string, freshness: MarketDataPoint["freshness"], confidence: MarketDataPoint["confidence"], sourceUrl?: string, limitation?: string): MarketDataPoint {
  return { key, label, value, unit: unit || undefined, changePct: changePct ?? null, source, sourceUrl, freshness, confidence, limitation };
}

async function yq(symbol: string, label: string): Promise<Quote> {
  try {
    const r = await fetch(YF + encodeURIComponent(symbol) + "?interval=15m&range=1d", { headers: { "User-Agent": UA }, next: { revalidate: 120 } });
    if (!r.ok) throw new Error(String(r.status));
    const j: any = await r.json(); const res = j?.chart?.result?.[0]; const m = res?.meta ?? {};
    const price = num(m.regularMarketPrice); const prev = num(m.chartPreviousClose) ?? num(m.previousClose);
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

export async function getGSecYield(): Promise<GSecYield> {
  return cached("gsec", 20 * 60_000, async () => {
    const res = await searchSources(["India 10 year G-Sec government bond yield today", "India 10Y benchmark bond yield latest"]);
    let y: number | null = null; let src = res[0];
    for (const r of res.slice(0, 4)) { const v = pctIn(r.snippet || "", 5, 9); if (v != null) { y = v; src = r; break; } }
    if (y != null && src) return { yield10Y: y, changeBps: null, date: src.published, source: src.source, sourceUrl: src.url, freshness: "latest_available", confidence: "retrieved", limitation: "10Y G-Sec change (bps) unavailable; level from latest retrieved source." };
    return { yield10Y: null, source: "Maven analysis", freshness: "unavailable", confidence: "unavailable", limitation: "10Y G-Sec yield unavailable from current sources." };
  });
}
export async function getFIIDIIFlows(): Promise<FiiDiiFlows> {
  return cached("fiidii", 45 * 60_000, async () => {
    const res = await searchSources(["FII DII activity today India cash market net buy sell crore", "FPI DII provisional cash data NSE today"]);
    const top = res[0];
    if (top) return { fiiCashNet: null, diiCashNet: null, context: top.snippet, date: top.published, source: top.source, sourceUrl: top.url, freshness: "latest_available", confidence: "retrieved", limitation: "Live FII/DII feed unavailable; using latest retrieved institutional-flow context." };
    return { fiiCashNet: null, diiCashNet: null, source: "Maven analysis", freshness: "unavailable", confidence: "unavailable", limitation: "FII/DII flow data unavailable from current sources." };
  });
}
export async function getIndiaMacroSnapshot(): Promise<MacroSnapshot> {
  const [crude, usdinr] = await Promise.all([getCrudePrice(), getUSDINR()]);
  const points: MarketDataPoint[] = [];
  if (crude.price != null) points.push(mdp("crude", "Brent crude", round2(crude.price), "USD/bbl", crude.changePct, "Yahoo Finance", "live", "retrieved"));
  if (usdinr.price != null) points.push(mdp("usdinr", "USD/INR", round2(usdinr.price), "", usdinr.changePct, "Yahoo Finance", "live", "retrieved"));
  const retrieved = await cached("macro_in", 12 * 3600_000, async () => {
    const out: MarketDataPoint[] = [];
    const defs: [string, string, string, number, number][] = [["cpi", "CPI inflation", "India CPI inflation latest rate percent", 0, 20], ["repo", "RBI repo rate", "India RBI repo rate current percent", 3, 10]];
    for (const [key, label, q, lo, hi] of defs) {
      const rs = await searchSources([q]); const r = rs[0]; if (!r) continue;
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

function classifyAnn(title: string, source: string): Announcement["type"] {
  const t = (title + " " + source).toLowerCase();
  if (/\bnse\b|\bbse\b|exchange|regulation 30|intimation|filing/.test(t)) return "exchange_announcement";
  if (/result|q[1-4]fy|quarter|earnings|profit|revenue/.test(t)) return "quarterly_result";
  if (/investor presentation|analyst meet|concall|earnings call/.test(t)) return "investor_presentation";
  if (/dividend|bonus|split|buyback|merger|acquisition|demerger|stake/.test(t)) return "corporate_action";
  if (/management|commentary|guidance|\bceo\b|\bmd\b/.test(t)) return "management_commentary";
  return "news_fallback";
}

export async function getCompanyAnnouncements(symbol: string, companyName?: string): Promise<CompanyAnnouncements> {
  const name = companyName || symbol;
  return cached("ann:" + symbol, 30 * 60_000, async () => {
    const res = await searchSources([
      `${name} NSE latest announcement`,
      `${name} BSE corporate announcement`,
      `${name} quarterly results latest`,
      `${name} investor presentation latest`,
      `${name} stock news today India`,
    ]);
    if (!res.length) return { symbol: symbol.toUpperCase(), announcements: [], limitation: "No recent company announcement found from current sources." };
    const announcements: Announcement[] = res.slice(0, 5).map((r) => ({ title: r.title, date: r.published, source: r.source, sourceUrl: r.url, snippet: r.snippet, type: classifyAnn(r.title, r.source), confidence: "retrieved" }));
    return { symbol: symbol.toUpperCase(), announcements };
  });
}

export async function getCompanySnapshot(symbol: string, companyName?: string): Promise<CompanySnapshot> {
  const sym = symbol.includes(".") ? symbol : symbol.toUpperCase() + ".NS";
  return cached("snap:" + sym, 120_000, async () => {
    const q = await getStockPrice(symbol);
    const s: CompanySnapshot = {
      symbol: symbol.toUpperCase(), companyName, sector: undefined, industry: undefined,
      price: q.price != null ? round2(q.price) : null, change: null, changePct: q.changePct != null ? round2(q.changePct) : null,
      marketCap: null, pe: null, pb: null, roe: null, roce: null, dividendYield: null, eps: null, bookValue: null, debtToEquity: null,
      revenueGrowth: null, profitGrowth: null, operatingMargin: null, netMargin: null,
      fiftyTwoWeekHigh: null, fiftyTwoWeekLow: null, resultDate: null,
      source: "Yahoo Finance", freshness: "live", confidence: "retrieved", unavailableFields: [],
    };
    try {
      const r = await fetch(QS + encodeURIComponent(sym) + "?modules=summaryDetail,defaultKeyStatistics,financialData,assetProfile,price", { headers: { "User-Agent": UA }, next: { revalidate: 1800 } });
      if (r.ok) {
        const j: any = await r.json(); const res = j?.quoteSummary?.result?.[0];
        const sd = res?.summaryDetail, ks = res?.defaultKeyStatistics, fd = res?.financialData, ap = res?.assetProfile, pr = res?.price;
        s.companyName = s.companyName || pr?.longName || pr?.shortName;
        s.sector = ap?.sector; s.industry = ap?.industry;
        const mc = num(pr?.marketCap?.raw) ?? num(sd?.marketCap?.raw); s.marketCap = mc != null ? Math.round(mc / 1e7) : null;
        s.pe = r2(sd?.trailingPE?.raw ?? ks?.trailingPE?.raw); s.pb = r2(ks?.priceToBook?.raw);
        s.roe = mulPct(fd?.returnOnEquity?.raw); s.dividendYield = mulPct(sd?.dividendYield?.raw);
        s.eps = r2(ks?.trailingEps?.raw); s.bookValue = r2(ks?.bookValue?.raw); s.debtToEquity = r2(fd?.debtToEquity?.raw);
        s.revenueGrowth = mulPct(fd?.revenueGrowth?.raw); s.profitGrowth = mulPct(fd?.earningsGrowth?.raw);
        s.operatingMargin = mulPct(fd?.operatingMargins?.raw); s.netMargin = mulPct(fd?.profitMargins?.raw);
        s.fiftyTwoWeekHigh = r2(sd?.fiftyTwoWeekHigh?.raw); s.fiftyTwoWeekLow = r2(sd?.fiftyTwoWeekLow?.raw);
      }
    } catch { /* graceful */ }
    if (s.pe == null || s.pb == null || s.roe == null || s.marketCap == null) {
      const rs = await searchSources([`${s.companyName || symbol} share P/E P/B ROE market cap NSE`]);
      const t = rs.map((x) => x.snippet).join(" "); const src = rs[0];
      const mark = () => { if (src) { s.sourceUrl = src.url; } s.confidence = "retrieved"; s.freshness = "latest_available"; };
      if (s.pe == null) { const v = numNear(t, /p\/e|pe ratio|price to earnings/, 2, 300); if (v != null) { s.pe = v; mark(); } }
      if (s.pb == null) { const v = numNear(t, /p\/b|pb ratio|price to book/, 0.1, 60); if (v != null) { s.pb = v; mark(); } }
      if (s.roe == null) { const v = pctNear(t, /roe|return on equity/, -60, 90); if (v != null) { s.roe = v; mark(); } }
    }
    const fields = ["marketCap", "pe", "pb", "roe", "roce", "dividendYield", "eps", "bookValue", "debtToEquity", "revenueGrowth", "profitGrowth", "operatingMargin", "netMargin", "fiftyTwoWeekHigh", "fiftyTwoWeekLow"];
    s.unavailableFields = fields.filter((k) => (s as any)[k] == null);
    if (s.pe == null && s.pb == null && s.roe == null && s.marketCap == null) s.limitation = "Detailed valuation metrics unavailable from current sources; price and market data shown.";
    return s;
  });
}

export async function getLatestResultContext(symbol: string, companyName?: string): Promise<ResultContext> {
  const name = companyName || symbol;
  return cached("result:" + symbol, 6 * 3600_000, async () => {
    const res = await searchSources([`${name} latest quarterly results revenue net profit YoY India`, `${name} Q results PAT revenue growth`]);
    const top = res[0]; const t = res.map((x) => x.snippet).join(" ");
    const rc: ResultContext = {
      resultDate: top?.published ?? null, revenue: null, ebitda: null, pat: null, margin: null,
      yoyRevenueGrowth: pctNear(t, /revenue (grew|rose|fell|up|down|yoy)|yoy revenue/, -90, 300),
      yoyProfitGrowth: pctNear(t, /(net profit|pat|profit) (grew|rose|fell|jump|surg|declin|up|down|yoy)/, -99, 500),
      qoqRevenueGrowth: null, qoqProfitGrowth: null,
      keyCommentary: top?.snippet, source: top?.source ?? "Maven analysis", sourceUrl: top?.url, confidence: top ? "retrieved" : "unavailable", unavailableFields: [],
    };
    rc.unavailableFields = ["revenue", "ebitda", "pat", "margin", "qoqRevenueGrowth", "qoqProfitGrowth"].filter((k) => (rc as any)[k] == null);
    if (!top) rc.limitation = "Latest quarterly result details unavailable from current sources.";
    else if (rc.yoyRevenueGrowth == null && rc.yoyProfitGrowth == null) rc.limitation = "Exact quarterly figures not parsed; latest result context shown from retrieved source.";
    return rc;
  });
}

export async function getShareholdingContext(symbol: string, companyName?: string): Promise<ShareholdingContext> {
  const name = companyName || symbol;
  return cached("shp:" + symbol, 12 * 3600_000, async () => {
    const res = await searchSources([`${name} shareholding pattern promoter FII DII holding latest percent`]);
    const top = res[0]; const t = res.map((x) => x.snippet).join(" ");
    const sh: ShareholdingContext = {
      date: top?.published ?? null,
      promoterHolding: pctNear(t, /promoter/, 0, 100), fiiHolding: pctNear(t, /fii|fpi|foreign/, 0, 100),
      diiHolding: pctNear(t, /dii|domestic institution|mutual fund/, 0, 100), publicHolding: pctNear(t, /public/, 0, 100),
      pledgedHolding: pctNear(t, /pledge/, 0, 100),
      source: top?.source ?? "Maven analysis", sourceUrl: top?.url, confidence: top ? "retrieved" : "unavailable",
    };
    if (!top || (sh.promoterHolding == null && sh.fiiHolding == null)) sh.limitation = "Latest shareholding pattern unavailable from current sources.";
    return sh;
  });
}
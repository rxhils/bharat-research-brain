import type { Quote, SectorPerf, FiiDiiFlows, GSecYield, MacroSnapshot, MarketDataPoint, CompanyAnnouncements, Announcement, CompanySnapshot, ResultContext, ShareholdingContext, StockMover, StockMoverParams, StockMoversResult, StockMoverDirection, StockMoverUniverse } from "./types";
import { searchSources } from "./sourceSearch";
import { normalizeForClassification } from "./queryNormalizer";
import { getActiveEquityUniverse } from "./activeEquityUniverse";
import { parseSectorScope, symbolInScope, industryOf, sectorLabelOf, sectorNoteOf, type SectorScope } from "./sectorClassifier";

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
// A tradeable price is strictly positive. Yahoo historical daily series sometimes carry a 0 (or
// null) close on a data-gap day; treat those as missing, never as a real price of zero - otherwise
// a 0 close yields a fake -100% move and can propagate NaN into charts.
const posNum = (x: unknown): number | null => { const n = num(x); return n != null && n > 0 ? n : null; };
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

// Historical single-day quote: daily candles over a 3mo lookback (covers "last month"/"last Friday"
// asks), matched to `date` (YYYY-MM-DD, UTC candle date). Never fabricates - if `date` isn't in the
// returned candles (holiday/no data/future), returns a null quote so the caller emits a limitation.
async function yqHistorical(symbol: string, label: string, date: string): Promise<Quote> {
  try {
    const r = await fetch(YF + encodeURIComponent(symbol) + "?interval=1d&range=3mo", { headers: { "User-Agent": UA }, next: { revalidate: 1800 } });
    if (!r.ok) throw new Error(String(r.status));
    const j: any = await r.json(); const res = j?.chart?.result?.[0];
    const timestamps: number[] = res?.timestamp ?? [];
    const closes: (number | null)[] = res?.indicators?.quote?.[0]?.close ?? [];
    const idx = timestamps.findIndex((ts) => new Date(ts * 1000).toISOString().slice(0, 10) === date);
    if (idx === -1) return { label, symbol, price: null, changePct: null };
    // posNum rejects 0/negative/NaN closes so a Yahoo data-gap day reads as "unavailable" (null),
    // not a fake price. changePct compares against the nearest strictly-valid prior close, so it is
    // never NaN/Infinity even when intermediate candles are missing.
    const price = posNum(closes[idx]);
    let prior: number | null = null;
    for (let i = idx - 1; i >= 0; i--) { const v = posNum(closes[i]); if (v != null) { prior = v; break; } }
    return { label, symbol, price, changePct: price != null && prior != null ? ((price - prior) / prior) * 100 : null };
  } catch { return { label, symbol, price: null, changePct: null }; }
}

const INDICES: [string, string][] = [["^NSEI", "Nifty 50"], ["^BSESN", "Sensex"], ["^NSEBANK", "Bank Nifty"], ["^CNXMIDCAP", "Nifty Midcap"], ["^CNXSC", "Nifty Smallcap"]];
const SECTORS: [string, string][] = [["^NSEBANK", "Banks"], ["^CNXIT", "IT"], ["^CNXAUTO", "Auto"], ["^CNXPHARMA", "Pharma"], ["^CNXFMCG", "FMCG"], ["^CNXENERGY", "Energy"], ["^CNXMETAL", "Metal"], ["^CNXREALTY", "Realty"]];

export async function getIndexPerformance(index?: string, opts?: { date?: string }): Promise<Quote[]> {
  const date = opts?.date;
  return cached("indices:" + (index ?? "all") + (date ? ":" + date : ""), 120_000, async () => {
    const set = index ? INDICES.filter(([, l]) => l.toLowerCase().includes(index.toLowerCase())) : INDICES;
    const use = set.length ? set : INDICES;
    return Promise.all(use.map(([s, l]) => (date ? yqHistorical(s, l, date) : yq(s, l))));
  });
}
export async function getSectorPerformance(opts?: { date?: string }): Promise<SectorPerf[]> {
  const date = opts?.date;
  return cached("sectors" + (date ? ":" + date : ""), 240_000, async () => {
    const qs = await Promise.all(SECTORS.map(([s, l]) => (date ? yqHistorical(s, l, date) : yq(s, l))));
    return qs.filter((q) => q.changePct != null).map((q) => ({ name: q.label, changePct: q.changePct as number })).sort((a, b) => b.changePct - a.changePct);
  });
}
export async function getStockPrice(symbol: string): Promise<Quote> {
  const sym = symbol.includes(".") ? symbol : symbol.toUpperCase() + ".NS";
  return cached("price:" + sym, 120_000, () => yq(sym, symbol.toUpperCase()));
}
export async function getCrudePrice(opts?: { date?: string }): Promise<Quote> {
  const date = opts?.date;
  return cached("crude" + (date ? ":" + date : ""), 180_000, () => (date ? yqHistorical("BZ=F", "Brent crude", date) : yq("BZ=F", "Brent crude")));
}
export async function getUSDINR(opts?: { date?: string }): Promise<Quote> {
  const date = opts?.date;
  return cached("usdinr" + (date ? ":" + date : ""), 120_000, () => (date ? yqHistorical("INR=X", "USD / INR", date) : yq("INR=X", "USD / INR")));
}

export async function getGSecYield(opts?: { date?: string }): Promise<GSecYield> {
  const date = opts?.date;
  return cached("gsec" + (date ? ":" + date : ""), 20 * 60_000, async () => {
    const queries = date
      ? [`India 10 year G-Sec government bond yield ${date}`, `India 10Y benchmark bond yield ${date}`]
      : ["India 10 year G-Sec government bond yield today", "India 10Y benchmark bond yield latest"];
    const res = await searchSources(queries);
    let y: number | null = null; let src = res[0];
    for (const r of res.slice(0, 4)) { const v = pctIn(r.snippet || "", 5, 9); if (v != null) { y = v; src = r; break; } }
    if (y != null && src) return { yield10Y: y, changeBps: null, date: src.published, source: src.source, sourceUrl: src.url, freshness: "latest_available", confidence: "retrieved", limitation: date ? "10Y G-Sec figure is the closest retrievable for that date and may be approximate." : "10Y G-Sec change (bps) unavailable; level from latest retrieved source." };
    return { yield10Y: null, source: "Maven analysis", freshness: "unavailable", confidence: "unavailable", limitation: "10Y G-Sec yield unavailable from current sources." };
  });
}
export async function getFIIDIIFlows(opts?: { date?: string }): Promise<FiiDiiFlows> {
  const date = opts?.date;
  return cached("fiidii" + (date ? ":" + date : ""), 45 * 60_000, async () => {
    const queries = date
      ? [`FII DII activity ${date} India cash market net buy sell crore`, `FPI DII provisional cash data NSE ${date}`]
      : ["FII DII activity today India cash market net buy sell crore", "FPI DII provisional cash data NSE today"];
    const res = await searchSources(queries);
    const top = res[0];
    if (top) return { fiiCashNet: null, diiCashNet: null, context: top.snippet, date: top.published, source: top.source, sourceUrl: top.url, freshness: "latest_available", confidence: "retrieved", limitation: date ? "FII/DII figure is the closest retrievable for that date and may be approximate." : "Live FII/DII feed unavailable; using latest retrieved institutional-flow context." };
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

// ---- Top stock movers (individual-stock leaderboard) ----
// Ranks INDIVIDUAL NSE/BSE equities. Never uses index moves as a proxy and never fabricates rows:
// if a real leaderboard cannot be built, it returns an empty list + a clean, non-technical
// limitation so the answer layer says the data was unavailable rather than guessing.
// No predefined screener maps to "contributors" - that direction is scan-only (guarded below).
const SCR_ID: Partial<Record<StockMoverDirection, string>> = { gainers: "day_gainers", losers: "day_losers", most_active: "most_actives" };

export function parseMoverParams(query: string): StockMoverParams {
  const n = normalizeForClassification(query || "");
  // Order matters: "which stocks pulled IT down?" is a losers ask (down), not a generic
  // contributors ask; "which stocks drove realty today?" (no direction word) is contributors.
  const direction: StockMoverDirection =
    /\b(losers?|fell|fallen|declin|decreas|dropp?ed|worst|down)\b/.test(n) ? "losers"
    : /\b(most active|active|volume|traded)\b/.test(n) ? "most_active"
    : /\b(drove|led|pulled|pushed|caused|contribut|behind the (move|rally|fall)|moved the most)\b/.test(n) ? "contributors"
    : "gainers";
  const m = n.match(/\btop\s+(\d{1,3})\b/);
  const limit = Math.max(1, Math.min(m ? parseInt(m[1], 10) : 5, 25));
  const sector = parseSectorScope(query || "", n);
  return { direction, limit, universe: "nifty500", sectorScope: sector?.scope };
}

async function yahooScreenerMovers(direction: StockMoverDirection, limit: number): Promise<StockMover[]> {
  const scrId = SCR_ID[direction];
  if (!scrId) return [];
  try {
    const url = `https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?count=${Math.min(limit * 4, 50)}&scrIds=${scrId}&region=IN&lang=en-IN`;
    const r = await fetch(url, { headers: { "User-Agent": UA }, next: { revalidate: 120 } });
    if (!r.ok) return [];
    const j: any = await r.json();
    const quotes: any[] = j?.finance?.result?.[0]?.quotes ?? [];
    const raw = (v: any) => (v && typeof v === "object" && "raw" in v ? v.raw : v);
    const movers: StockMover[] = [];
    for (const q of quotes) {
      const sym = String(q?.symbol ?? "");
      // NSE/BSE equities only - never indices/ETFs/REITs, never non-Indian listings.
      if (!/\.(NS|BO)$/i.test(sym)) continue;
      if (q?.quoteType && String(q.quoteType).toUpperCase() !== "EQUITY") continue;
      const price = num(raw(q?.regularMarketPrice));
      const change = num(raw(q?.regularMarketChange));
      const changePct = num(raw(q?.regularMarketChangePercent));
      const bare = sym.replace(/\.(NS|BO)$/i, "");
      movers.push({
        symbol: bare, companyName: String(q?.longName ?? q?.shortName ?? bare),
        price: price != null ? round2(price) : null,
        change: change != null ? round2(change) : null,
        changePct: changePct != null ? round2(changePct) : null,
        volume: num(raw(q?.regularMarketVolume)), tradedValue: null,
        sector: typeof q?.sector === "string" ? q.sector : null,
        source: "Yahoo Finance screener", sourceUrl: `https://finance.yahoo.com/quote/${encodeURIComponent(sym)}`,
        freshness: "live", confidence: "retrieved",
      });
      if (movers.length >= limit) break;
    }
    return movers;
  } catch { return []; }
}

// ---- keyless mover scan (curated liquid universe) ----
// Per-symbol v8 quote: price + change% + volume from chart meta (the v7 batch endpoint 401s
// without a crumb/cookie, which we do NOT bypass).
async function yqMover(sym: string): Promise<{ price: number | null; changePct: number | null; volume: number | null }> {
  try {
    const r = await fetch(YF + encodeURIComponent(sym) + "?interval=1d&range=1d", { headers: { "User-Agent": UA }, next: { revalidate: 120 } });
    if (!r.ok) return { price: null, changePct: null, volume: null };
    const j: any = await r.json(); const m = j?.chart?.result?.[0]?.meta ?? {};
    const price = posNum(m.regularMarketPrice);
    const prev = posNum(m.chartPreviousClose) ?? posNum(m.previousClose);
    const changePct = price != null && prev != null ? round2(((price - prev) / prev) * 100) : null;
    return { price: price != null ? round2(price) : null, changePct, volume: num(m.regularMarketVolume) };
  } catch { return { price: null, changePct: null, volume: null }; }
}

// Rolling per-symbol quote cache + rotating cursor. Each scan window (bounded by concurrency and
// a wall-clock deadline) refreshes as many quotes as it can, starting where the previous window
// stopped; the leaderboard then ranks over ALL quotes still fresh in the cache. Coverage of the
// Nifty 500 therefore ACCUMULATES across scan windows instead of being capped by a single window,
// while any single request stays inside the strict deadline.
const QUOTE_TTL = 10 * 60_000;
const MOVER_QUOTES = new Map<string, { price: number | null; changePct: number | null; volume: number | null; at: number }>();
let scanCursor = 0;

async function runScan(symbols: { symbol: string; name: string }[], concurrency: number, deadlineMs: number): Promise<void> {
  const n = symbols.length;
  if (!n) return;
  const deadline = Date.now() + deadlineMs;
  const start = scanCursor % n;
  let offset = 0;
  const worker = async () => {
    while (Date.now() < deadline) {
      const my = offset++;
      if (my >= n) break;
      const s = symbols[(start + my) % n];
      const c = MOVER_QUOTES.get(s.symbol);
      if (c && Date.now() - c.at < QUOTE_TTL) continue; // still fresh - skip, spend budget on stale ones
      const q = await yqMover(s.symbol + ".NS");
      MOVER_QUOTES.set(s.symbol, { ...q, at: Date.now() });
    }
  };
  await Promise.all(Array.from({ length: Math.min(concurrency, n) }, worker));
  scanCursor = (start + Math.min(offset, n)) % n; // next window continues where this one stopped
}

async function scanMoversFromUniverse(direction: StockMoverDirection, limit: number, sectorScope?: string): Promise<{
  movers: StockMover[]; limitation?: string; universeLabel: string; universeSize: number; covered: number; coverage: string;
  sectorScope?: string; sectorLabel?: string;
}> {
  const uni = await getActiveEquityUniverse();
  // Spec guardrails: concurrency 5, strict ~10s wall-clock deadline. The rolling cache means a
  // partial first window still yields a real (labeled) leaderboard, and coverage grows per window.
  await runScan(uni.symbols, 5, 10_000);
  let rows: StockMover[] = [];
  for (const s of uni.symbols) {
    const q = MOVER_QUOTES.get(s.symbol);
    // Data-quality rule: a row needs symbol + real price + change%, else excluded (never guessed).
    if (!q || Date.now() - q.at >= QUOTE_TTL || q.price == null || q.changePct == null) continue;
    rows.push({
      symbol: s.symbol, companyName: s.name, price: q.price, change: null, changePct: q.changePct,
      volume: q.volume ?? null, tradedValue: null,
      sector: industryOf(s.symbol) ?? null, // real NSE industry from the committed snapshot
      source: "Market data · latest available", sourceUrl: `https://finance.yahoo.com/quote/${encodeURIComponent(s.symbol)}.NS`,
      freshness: "latest_available", confidence: "retrieved",
    });
  }
  const covered = rows.length;
  const scope = sectorScope as SectorScope | undefined;
  const scopeLabel = scope ? sectorLabelOf(scope) : undefined;
  const base = {
    universeLabel: uni.universeLabel, universeSize: uni.universeSize, covered, coverage: uni.coverage,
    sectorScope: scope, sectorLabel: scopeLabel,
  };
  // Sector filter AFTER quotes: only symbols whose committed NSE industry matches the scope.
  // Symbols without sector metadata are excluded from sector-scoped rankings, never guessed in.
  if (scope) rows = rows.filter((r) => symbolInScope(r.symbol, r.companyName, scope));
  if (!rows.length) {
    return {
      movers: [], ...base,
      limitation: scope
        ? `No fresh quotes for Nifty 500 ${scopeLabel} names in the latest scan window; Maven will not guess the stocks.`
        : undefined,
    };
  }
  // "contributors" ranks by size of move (either direction) with liquidity as tie-break - labeled
  // as movers, NOT verified index contribution (no free-float weight data in the keyless path).
  const sorted = direction === "losers" ? rows.sort((a, b) => (a.changePct ?? 0) - (b.changePct ?? 0))
    : direction === "most_active" ? rows.sort((a, b) => (b.volume ?? -1) - (a.volume ?? -1))
    : direction === "contributors" ? rows.sort((a, b) => Math.abs(b.changePct ?? 0) - Math.abs(a.changePct ?? 0) || (b.volume ?? -1) - (a.volume ?? -1))
    : rows.sort((a, b) => (b.changePct ?? 0) - (a.changePct ?? 0));
  // Honest coverage wording (never claims "all NSE"): exact counts for the scanned universe.
  const parts: string[] = [];
  if (scope) {
    parts.push(`Latest available ${scopeLabel} movers from the Nifty 500 universe (${rows.length} ${scopeLabel} name${rows.length === 1 ? "" : "s"} with fresh quotes; ${covered} of ${uni.universeSize} constituents covered in the latest scan window).`);
    const note = sectorNoteOf(scope);
    if (note) parts.push(note);
  } else {
    parts.push(uni.coverage === "nifty500"
      ? `Latest available movers from the Nifty 500 universe (quotes covered ${covered} of ${uni.universeSize} constituents in the latest scan window).`
      : `Latest available movers from a curated liquid NSE universe (${covered} of ${uni.universeSize} symbols quoted).`);
  }
  if (direction === "contributors") {
    parts.push("Free-float contribution data was unavailable, so Maven ranked individual movers by size of latest percentage move and liquidity - movers, not verified index contribution.");
  }
  return { movers: sorted.slice(0, limit), limitation: parts.join(" "), ...base };
}

export async function getTopStockMovers(params: StockMoverParams): Promise<StockMoversResult> {
  const { direction, limit } = params;
  const universe: StockMoverUniverse = params.universe ?? "nse_equity";
  const date = params.date;
  const ttl = date ? 24 * 3600_000 : 3 * 60_000; // today refreshes every few minutes; history is fixed
  return cached(`stock_movers:${direction}:${universe}:${params.sectorScope ?? "all"}:${date ?? "today"}`, ttl, async (): Promise<StockMoversResult> => {
    const base = { direction, limit, universe, date };
    // Live leaderboard only for "today" - a historical single-day mover ranking isn't reconstructable
    // from the live screener, so those go straight to the honest-unavailable path.
    if (!date) {
      // 1) Yahoo predefined screener (returns US listings for India; filtered to NSE/BSE, usually
      //    empty). Skipped for sector-scoped or contributor asks - it carries no sector metadata.
      if (!params.sectorScope && direction !== "contributors") {
        const screened = await yahooScreenerMovers(direction, limit);
        if (screened.length) {
          return { ...base, movers: screened, source: "Market data · latest available", sourceUrl: "https://finance.yahoo.com/screener",
            freshness: "live", confidence: "retrieved", limitation: "Ranked from the available equity screener; may not span every NSE stock." };
        }
      }
      // 2) Primary keyless path: rolling batch-scan of the active-equity universe (Nifty 500
      //    primary, curated liquid fallback) via per-symbol quotes, sector-filtered if asked.
      const scanned = await scanMoversFromUniverse(direction, limit, params.sectorScope);
      if (scanned.movers.length) {
        return { ...base, universe: scanned.coverage === "nifty500" ? "nifty500" : "nifty50",
          movers: scanned.movers, source: "Market data · latest available",
          sourceUrl: "https://finance.yahoo.com", freshness: "latest_available", confidence: "retrieved",
          limitation: scanned.limitation,
          universeLabel: scanned.universeLabel, universeSize: scanned.universeSize, coveredCount: scanned.covered,
          sectorScope: scanned.sectorScope, sectorLabel: scanned.sectorLabel };
      }
      // Sector asked but no fresh sector quotes: return the honest sector-specific unavailable
      // (never index/sector prose, never a different sector's stocks).
      if (params.sectorScope) {
        return { ...base, movers: [], source: "Market data · latest available",
          freshness: "unavailable", confidence: "unavailable",
          limitation: scanned.limitation ?? "Sector mover data was unavailable from current sources; Maven will not guess the stocks.",
          universeLabel: scanned.universeLabel, universeSize: scanned.universeSize, coveredCount: scanned.covered,
          sectorScope: scanned.sectorScope, sectorLabel: scanned.sectorLabel };
      }
    }
    // Fallback: cite a retrieved market-mover source but NEVER fabricate a ranked table.
    const dirWord = direction === "losers" ? "top losers" : direction === "most_active" ? "most active stocks" : "top gainers";
    const res = await searchSources([`NSE ${dirWord} today India`, `${dirWord} Indian stock market today Moneycontrol`]);
    const top = res[0];
    return {
      ...base, movers: [], source: top?.source ?? "Maven analysis", sourceUrl: top?.url,
      freshness: "unavailable", confidence: "unavailable",
      limitation: date
        ? "A verified historical top-mover table for that date was unavailable from current sources; Maven will not guess the individual stocks."
        : "Exact top-mover data was unavailable from current sources; Maven will not guess the individual stocks. See the retrieved market source for context.",
    };
  });
}
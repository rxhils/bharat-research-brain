import type { SourceResult, Confidence, ExtractedPage } from "./types";
import { searchSearxngMany, searxngConfigured } from "./freeSourceSearch";
import { extractPage } from "./pageExtractor";

// Source retrieval pipeline (India-first):
//   official-domain queries -> SearXNG (free) -> paid provider fallback -> rank -> extract -> dedupe.
// Paid providers (Tavily/Serper/Exa/Brave) are only used when the free layer didn't find enough,
// and are kept intact so nothing regresses. No provider/scraper error is ever surfaced to the user.

type Provider = "tavily" | "serper" | "exa" | "brave" | null;

function pickProvider(): Provider {
  if (process.env.TAVILY_API_KEY) return "tavily";
  if (process.env.SERPER_API_KEY) return "serper";
  if (process.env.EXA_API_KEY) return "exa";
  if (process.env.BRAVE_API_KEY) return "brave";
  return null;
}

function hostOf(u: string): string { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return "source"; } }

// ---- paid providers (unchanged behaviour, kept as fallback) ----
async function tavily(q: string): Promise<SourceResult[]> {
  const r = await fetch("https://api.tavily.com/search", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: process.env.TAVILY_API_KEY, query: q, max_results: 4, search_depth: "basic" }),
    cache: "no-store",
  });
  if (!r.ok) return [];
  const j: any = await r.json();
  return (j?.results || []).map((x: any): SourceResult => ({ title: x.title, url: x.url, snippet: x.content || "", source: hostOf(x.url), provider: "tavily" }));
}
async function serper(q: string): Promise<SourceResult[]> {
  const r = await fetch("https://google.serper.dev/news", {
    method: "POST", headers: { "Content-Type": "application/json", "X-API-KEY": process.env.SERPER_API_KEY || "" },
    body: JSON.stringify({ q, gl: "in", num: 4 }), cache: "no-store",
  });
  if (!r.ok) return [];
  const j: any = await r.json();
  return (j?.news || j?.organic || []).slice(0, 4).map((x: any): SourceResult => ({ title: x.title, url: x.link, snippet: x.snippet || "", source: x.source || hostOf(x.link), published: x.date, provider: "serper" }));
}
async function exa(q: string): Promise<SourceResult[]> {
  const r = await fetch("https://api.exa.ai/search", {
    method: "POST", headers: { "Content-Type": "application/json", "x-api-key": process.env.EXA_API_KEY || "" },
    body: JSON.stringify({ query: q, numResults: 4, contents: { text: true } }), cache: "no-store",
  });
  if (!r.ok) return [];
  const j: any = await r.json();
  return (j?.results || []).map((x: any): SourceResult => ({ title: x.title, url: x.url, snippet: (x.text || "").slice(0, 280), source: hostOf(x.url), published: x.publishedDate, provider: "exa" }));
}
async function brave(q: string): Promise<SourceResult[]> {
  const r = await fetch("https://api.search.brave.com/res/v1/news/search?q=" + encodeURIComponent(q) + "&country=in&count=4", {
    headers: { "X-Subscription-Token": process.env.BRAVE_API_KEY || "", Accept: "application/json" }, cache: "no-store",
  });
  if (!r.ok) return [];
  const j: any = await r.json();
  return (j?.results || []).slice(0, 4).map((x: any): SourceResult => ({ title: x.title, url: x.url, snippet: x.description || "", source: hostOf(x.url), published: x.age, provider: "brave" }));
}

async function runPaid(queries: string[]): Promise<SourceResult[]> {
  const provider = pickProvider();
  if (!provider) return [];
  const run = provider === "tavily" ? tavily : provider === "serper" ? serper : provider === "exa" ? exa : brave;
  const settled = await Promise.allSettled(queries.slice(0, 3).map((q) => run(q)));
  return settled.flatMap((s) => (s.status === "fulfilled" ? s.value : []));
}

// ---- official-domain query construction (task 4) ----
// Prepend exchange/regulator-scoped queries so official filings surface before general news.
function officialQueries(queries: string[]): string[] {
  const q0 = queries[0] || "";
  const joined = queries.join(" ").toLowerCase();
  const out: string[] = [];
  if (q0) { out.push(`site:nseindia.com ${q0}`); out.push(`site:bseindia.com ${q0}`); }
  if (/\brbi\b|repo rate|monetary policy|\bmpc\b/.test(joined)) out.push(`site:rbi.org.in ${q0 || queries[1] || ""}`.trim());
  if (/\bsebi\b|circular|regulation/.test(joined)) out.push(`site:sebi.gov.in ${q0 || queries[1] || ""}`.trim());
  return out.filter((s) => s.length > 12);
}

// ---- source ranking (task 6) ----
const REGULATOR = /(^|\.)(nseindia\.com|bseindia\.com|rbi\.org\.in|sebi\.gov\.in)$/i;
const MEDIA = /(thehindubusinessline|businessline|livemint|mint\.|economictimes|business-standard|moneycontrol|reuters|bloomberg|cnbctv18|financialexpress|ndtvprofit|thehindu)\./i;
const FILING_PATH = /(investor-presentation|investor-relations|annual-report|quarterly|financial-result|results|shareholding|regulation-filings|corporate-announcement)/i;

// Returns { rank, confidence }: 1 = exchange/regulator, 2 = investor relations,
// 3 = filings/presentations, 4 = reputable media, 5 = other finance/news, 6 = generic.
function classify(url: string): { rank: number; confidence: Confidence } {
  const host = hostOf(url);
  const path = (() => { try { return new URL(url).pathname.toLowerCase(); } catch { return ""; } })();
  if (REGULATOR.test(host)) return { rank: 1, confidence: "verified" };
  if (/(^|\.)(investor|ir)\./i.test(host) || /investor|shareholding-pattern/.test(path)) return { rank: 2, confidence: "verified" };
  if (FILING_PATH.test(path) || (/\.pdf($|\?)/i.test(path) && !MEDIA.test(host))) return { rank: 3, confidence: "verified" };
  if (MEDIA.test(host)) return { rank: 4, confidence: "retrieved" };
  if (/(news|market|finance|stock|invest|business)/i.test(host)) return { rank: 5, confidence: "retrieved" };
  return { rank: 6, confidence: "retrieved" };
}

function normUrl(u: string): string {
  try { const x = new URL(u); return (x.hostname.replace(/^www\./, "") + x.pathname.replace(/\/$/, "")).toLowerCase(); } catch { return u.toLowerCase(); }
}
function normTitle(t: string): string { return (t || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim(); }

function rankAndDedupe(list: SourceResult[]): SourceResult[] {
  const byUrl = new Set<string>();
  const byDomTitle = new Set<string>();
  const out: SourceResult[] = [];
  for (const s of list) {
    if (!s.url) continue;
    const nu = normUrl(s.url);
    const dt = hostOf(s.url) + "|" + normTitle(s.title);
    if (byUrl.has(nu) || byDomTitle.has(dt)) continue;
    byUrl.add(nu); byDomTitle.add(dt);
    const c = classify(s.url);
    out.push({
      ...s, domain: hostOf(s.url), sourceRank: c.rank,
      confidence: c.confidence, freshness: s.freshness ?? "latest_available",
      date: s.date ?? s.published,
    });
  }
  out.sort((a, b) => (a.sourceRank ?? 9) - (b.sourceRank ?? 9));
  return out;
}

// ---- extraction enrichment (task 7), bounded and best-effort ----
// Only the top-`n` slots are eligible, and within those we extract a page only when its search
// snippet is thin or it is an official filing - so rich snippets (e.g. Tavily) are not re-fetched
// and prod latency stays low. Failures are silent (extractionStatus: "failed", snippet retained).
async function enrichTop(list: SourceResult[], n: number): Promise<SourceResult[]> {
  const targets = list.map((s, i) => ({ s, i })).filter(({ s, i }) => i < n && ((s.snippet || "").length < 300 || (s.sourceRank ?? 9) <= 3));
  const settled = await Promise.allSettled(targets.map(({ s }) => extractPage(s.url)));
  const byIdx = new Map<number, ExtractedPage | null>();
  targets.forEach(({ i }, k) => { const r = settled[k]; byIdx.set(i, r.status === "fulfilled" ? r.value : null); });
  return list.map((s, i) => {
    if (!byIdx.has(i)) return s;
    const p = byIdx.get(i);
    if (!p || p.extractionStatus === "failed" || !p.text) return { ...s, extractionStatus: "failed" as const };
    return { ...s, title: s.title || p.title, snippet: p.text.slice(0, 1500) || s.snippet, date: s.date ?? p.date, extractionStatus: p.extractionStatus };
  });
}

export async function searchSources(queries: string[]): Promise<SourceResult[]> {
  if (!queries.length) return [];
  const qs = queries.slice(0, 4);

  // 1 + 2: official-domain queries and plain queries through the free SearXNG layer.
  const free = searxngConfigured() ? await searchSearxngMany([...officialQueries(qs), ...qs].slice(0, 8)) : [];
  let ranked = rankAndDedupe(free);

  // 3: only reach for a paid provider when the free layer didn't find enough official/quality sources.
  const enough = ranked.some((r) => (r.sourceRank ?? 9) <= 3) || ranked.length >= 3;
  if (!enough && pickProvider()) {
    const paid = await runPaid(qs);
    ranked = rankAndDedupe([...free, ...paid]);
  }

  // 7: keep 5-7, enrich the top slots with extracted page text (targeted, bounded, silent on failure).
  const top = ranked.slice(0, 7);
  return enrichTop(top, 5);
}

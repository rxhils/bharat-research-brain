import type { SourceResult, Confidence, ExtractedPage, DocumentType, SourceTier } from "./types";
import { searchSearxngMany, searxngConfigured } from "./freeSourceSearch";
import { searchGoogleNewsMany } from "./googleNewsSearch";
import { extractPage } from "./pageExtractor";
import { scoreSource } from "./sourceQualityScorer";

// Source retrieval pipeline (India-first):
//   official-domain queries -> SearXNG + Google News RSS (both free, run unconditionally) ->
//   paid provider fallback -> rank -> extract -> dedupe.
// SearXNG needs a reachable instance (env-configured); Google News RSS needs neither a key nor a
// configured host, so it is the one free layer that reliably returns real sources even in an
// environment with no search provider set up at all. Paid providers (Tavily/Serper/Exa/Brave)
// are only used when the free layers didn't find enough, and are kept intact so nothing
// regresses. No provider/scraper error is ever surfaced to the user.

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

// ---- source ranking (task 6) ---- delegates to sourceQualityScorer.ts, the single source of
// truth for domain -> tier/score/official, so the classification list is never duplicated.
const TIER_RANK: Record<string, number> = { exchange: 1, investor_relations: 2, filing: 3, regulator: 1, media: 4, data_page: 5, generic: 6 };

function docTypeOf(url: string, title: string): DocumentType {
  const t = `${url} ${title}`.toLowerCase();
  if (/shareholding|shareholding-pattern/.test(t)) return "shareholding_pattern";
  if (/annual-report|annual report/.test(t)) return "annual_report";
  if (/investor-presentation|investor presentation/.test(t)) return "investor_presentation";
  if (/quarterly|q[1-4]\s*fy|results?\b/.test(t)) return "quarterly_result";
  if (/announcement|corporate-announcement/.test(t)) return "exchange_announcement";
  if (/nseindia\.com|bseindia\.com/.test(t)) return "exchange_announcement";
  if (/thehindubusinessline|businessline|livemint|mint\.|economictimes|business-standard|moneycontrol|reuters|bloomberg|cnbctv18|ndtvprofit/.test(t)) return "news";
  return "other";
}

// Returns { rank, confidence }: 1 = exchange/regulator, 2 = investor relations,
// 3 = filings/presentations, 4 = reputable media, 5 = other finance/news, 6 = generic.
function classify(url: string): { rank: number; confidence: Confidence; sourceQualityScore: number; sourceTier: SourceTier; official: boolean } {
  const q = scoreSource(url);
  const rank = TIER_RANK[q.sourceTier] ?? 6;
  const confidence: Confidence = rank <= 3 ? "verified" : "retrieved";
  return { rank, confidence, ...q };
}

// A source's own `url` is sometimes a redirector (e.g. Google News' news.google.com links) rather
// than the true publisher domain. When the provider supplied `domainHint` (the real domain, read
// from feed metadata - never guessed), classification and the displayed domain use that instead,
// so a Reuters/Economic Times article surfaced via Google News still ranks as reputable media
// instead of falling through to "generic". The clickable `url` itself is never altered.
function classifyKeyFor(s: SourceResult): string { return s.domainHint || s.url; }

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
    const key = classifyKeyFor(s);
    const c = classify(key);
    out.push({
      ...s, domain: hostOf(key), sourceRank: c.rank,
      confidence: c.confidence, freshness: s.freshness ?? "latest_available",
      date: s.date ?? s.published,
      sourceQualityScore: c.sourceQualityScore, sourceTier: c.sourceTier, official: c.official,
      docType: docTypeOf(key, s.title),
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

export async function searchSources(queries: string[], opts?: { budget?: number }): Promise<SourceResult[]> {
  if (!queries.length) return [];
  // budget scales how many sources we keep: light ~6, standard ~12, deep ~22. Default 8 (legacy).
  const budget = Math.max(4, Math.min(opts?.budget ?? 8, 25));
  const qCap = budget >= 18 ? 8 : budget >= 10 ? 6 : 4;
  const qs = queries.slice(0, qCap);

  // 1 + 2: official-domain queries and plain queries through the free SearXNG layer, plus the
  // free Google News RSS layer (news-style queries only - "site:" filters aren't meaningful to
  // Google News search). Both run unconditionally and concurrently; Google News needs no config,
  // so it is what keeps source counts real when SearXNG has no reachable instance.
  // newsQueries draws from the FULL incoming list (not `qs`) and is capped independently: since
  // official-domain queries are ordered first, slicing the combined list down to qCap before
  // filtering left the news layer with only 1-2 plain queries once official queries ate most of
  // the cap - starving exactly the deep-research tier this layer most needs to fill.
  const newsQueries = queries.filter((q) => !/^site:/i.test(q)).slice(0, qCap);
  const [free, news] = await Promise.all([
    searxngConfigured() ? searchSearxngMany([...officialQueries(qs), ...qs].slice(0, qCap * 2)) : Promise.resolve<SourceResult[]>([]),
    searchGoogleNewsMany(newsQueries, qCap),
  ]);
  let ranked = rankAndDedupe([...free, ...news]);

  // 3: only reach for a paid provider when the free layer didn't find enough official/quality sources.
  const enoughCount = budget >= 18 ? 6 : budget >= 10 ? 4 : 3;
  const enough = ranked.filter((r) => (r.sourceRank ?? 9) <= 3).length >= 2 || ranked.length >= enoughCount;
  if (!enough && pickProvider()) {
    const paid = await runPaid(qs);
    ranked = rankAndDedupe([...free, ...news, ...paid]);
  }

  // 7: keep up to the budget, enrich the top slots with extracted page text (bounded, silent on failure).
  const top = ranked.slice(0, budget);
  return enrichTop(top, Math.min(5, budget));
}

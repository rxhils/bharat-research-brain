import type { NseSecurity, StockResolution } from "./types";
import snapshot from "./data/nse-universe.json";

// Full NSE equity universe. The committed snapshot (built from NSE's published, downloadable
// securities files - not scraping) guarantees coverage on prod even when NSE blocks datacenter IPs.
// A best-effort in-memory refresh (daily TTL) keeps it current where the fetch is reachable.

type RawSec = { s: string; n: string; series?: string; listed?: string; isin?: string; segment?: string; status?: string; oldSymbols?: string[]; oldNames?: string[] };

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36";
const EQUITY_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv";
const REFRESH_TTL = 24 * 60 * 60 * 1000;

function toSec(r: RawSec): NseSecurity {
  return {
    symbol: r.s, companyName: r.n, series: r.series, isin: r.isin, dateOfListing: r.listed,
    segment: (r.segment as NseSecurity["segment"]) || "equity",
    yahooSymbol: r.s + ".NS", aliases: [], oldSymbols: r.oldSymbols || [], oldNames: r.oldNames || [],
    status: (r.status as NseSecurity["status"]) || "active", lastUpdated: (snapshot as any).generatedAt || "",
  };
}

let CACHE: NseSecurity[] = ((snapshot as any).securities as RawSec[]).map(toSec);
let INDEX = buildIndex(CACHE);
let lastRefresh = 0;

type Idx = { bySymbol: Map<string, NseSecurity>; byName: Map<string, NseSecurity>; byOldSymbol: Map<string, NseSecurity> };
function norm(s: string): string { return (s || "").toLowerCase().replace(/\b(ltd|limited|the)\b/g, " ").replace(/[^a-z0-9]+/g, " ").trim(); }
// abbreviation-tolerant: each subject word is a >=3-char prefix of the matching company word (e.g. "kpit tech" -> "kpit technologies")
function wordPrefix(subjWords: string[], nameWords: string[]): boolean {
  if (subjWords.length < 2 || subjWords.length > nameWords.length) return false;
  return subjWords.every((w, i) => w.length >= 3 && nameWords[i]?.startsWith(w));
}
function buildIndex(list: NseSecurity[]): Idx {
  const bySymbol = new Map<string, NseSecurity>(), byName = new Map<string, NseSecurity>(), byOldSymbol = new Map<string, NseSecurity>();
  for (const x of list) {
    bySymbol.set(x.symbol.toUpperCase(), x);
    byName.set(norm(x.companyName), x);
    for (const o of x.oldSymbols) byOldSymbol.set(o.toUpperCase(), x);
  }
  return { bySymbol, byName, byOldSymbol };
}

function parseCsv(txt: string): NseSecurity[] {
  const lines = txt.trim().split(/\r?\n/);
  const out: NseSecurity[] = [];
  for (const line of lines.slice(1)) {
    const c = line.split(",").map((x) => x.trim());
    if (c.length < 7 || !c[0]) continue;
    out.push({ symbol: c[0], companyName: c[1], series: c[2] || "EQ", dateOfListing: c[3], isin: c[6], segment: "equity", yahooSymbol: c[0] + ".NS", aliases: [], oldSymbols: [], oldNames: [], status: "active", lastUpdated: new Date().toISOString() });
  }
  return out;
}

export async function refreshNseUniverse(): Promise<NseSecurity[]> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 8000);
  try {
    const r = await fetch(EQUITY_URL, { headers: { "User-Agent": UA, Accept: "text/csv,*/*" }, signal: ctrl.signal, cache: "no-store" });
    if (!r.ok) return CACHE;
    const list = parseCsv(await r.text());
    if (list.length > 500) { CACHE = list; INDEX = buildIndex(list); lastRefresh = Date.now(); }
    return CACHE;
  } catch {
    return CACHE; // unreachable (e.g. datacenter IP blocked) -> keep committed snapshot, no user-facing error
  } finally {
    clearTimeout(timer);
  }
}

export async function loadNseUniverse(): Promise<NseSecurity[]> {
  if (Date.now() - lastRefresh > REFRESH_TTL) void refreshNseUniverse(); // fire-and-forget; snapshot serves immediately
  return CACHE;
}

export function getUniverseStats() {
  const by = (seg: string) => CACHE.filter((x) => x.segment === seg).length;
  return { total: CACHE.length, equity: by("equity"), sme: by("sme"), etf: by("etf"), reit: by("reit"), invit: by("invit"), lastUpdated: CACHE[0]?.lastUpdated || "" };
}

// strip leading intent phrases and trailing noise so we match the actual company subject
const LEAD = /^(?:why (?:is|are|did)|what (?:happened to|changed in|is|are|was|were)|what's|whats|explain|tell me about|profile of|analy[sz]e|give me (?:a )?(?:full )?research (?:view )?on|full research on|how is|latest (?:announcement|results?|news) (?:for|of)|shareholding pattern of|share holding pattern of)\s+/i;
// generic fallback for "latest <1-3 word topic> [update/news/data...] for/of <company>" phrasings
// not covered by the specific LEAD list above (e.g. "latest capex update for Blue Star").
const LEAD_GENERIC = /^latest\s+\S+(?:\s+\S+){0,3}?\s+(?:for|of)\s+/i;
function subjectOf(q: string): string {
  let s = q.trim().replace(/[?.!]+$/, "");
  for (let i = 0; i < 3; i++) s = s.replace(LEAD, "");
  if (LEAD_GENERIC.test(s)) s = s.replace(LEAD_GENERIC, "");
  s = s.replace(/\s+(moving today|moving|today|right now|in detail|doing|up|down|falling|rising)$/i, "").trim();
  return s;
}

// Resolve a free-text query to a specific NSE security. Order: exact symbol/old-symbol token ->
// exact company name -> distinctive prefix match -> ambiguous/not_found. Never guesses on ambiguity.
export function resolveFromUniverse(query: string): StockResolution {
  const q = (query || "").trim();
  if (!q) return { status: "not_found", confidence: 0, reason: "empty query" };

  // 1. exact symbol as a standalone token - but only when written as an ALL-CAPS ticker in the
  // original query, so common words ("oil", "power", "bank") don't collide with symbols (OIL, POWER).
  for (const tok of q.split(/[^A-Za-z0-9&]+/)) {
    if (tok.length < 3 || tok !== tok.toUpperCase() || !/[A-Z]/.test(tok)) continue;
    const hit = INDEX.bySymbol.get(tok) || INDEX.byOldSymbol.get(tok);
    if (hit) return { status: "resolved", primary: hit, confidence: 0.95, reason: `exact symbol ${tok}` };
  }

  const subj = norm(subjectOf(q));
  if (!subj || subj.length < 3) return { status: "not_found", confidence: 0, reason: "no company subject" };

  // 2. exact normalized company name
  const exact = INDEX.byName.get(subj);
  if (exact) return { status: "resolved", primary: exact, confidence: 0.9, reason: "exact company name" };

  // 3. the subject is a distinctive prefix of a company name (>=2 words, or one word >=6 chars)
  const words = subj.split(" ").filter(Boolean);
  if (words.length < 2 && subj.length < 6) return { status: "not_found", confidence: 0, reason: "subject too short" };
  const subjWords = words;
  const cands: NseSecurity[] = [];
  for (const x of CACHE) {
    const n = norm(x.companyName);
    if (n === subj || n.startsWith(subj + " ") || subj.startsWith(n + " ") || wordPrefix(subjWords, n.split(" "))) cands.push(x);
  }
  if (cands.length === 1) return { status: "resolved", primary: cands[0], confidence: 0.8, reason: "company prefix match" };
  if (cands.length > 1) {
    const top = cands.sort((a, b) => a.companyName.length - b.companyName.length);
    // if the shortest is an exact-name subset the others extend, still ambiguous across distinct symbols
    return { status: "ambiguous", candidates: top.slice(0, 5), confidence: 0.4, reason: "multiple companies match" };
  }
  return { status: "not_found", confidence: 0, reason: "no universe match" };
}

export function universeNameForSymbol(symbol: string): string | undefined {
  return INDEX.bySymbol.get(symbol.replace(/\.ns$/i, "").toUpperCase())?.companyName;
}
